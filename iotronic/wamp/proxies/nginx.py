# Copyright 2017 MDSLAB - University of Messina
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from iotronic.wamp.proxies.proxy import Proxy
from oslo_config import cfg
from oslo_log import log as logging
from subprocess import call

LOG = logging.getLogger(__name__)

nginx_opts = [
    cfg.StrOpt('nginx_path',
               default='/etc/nginx/conf.d/iotronic',
               help=('Default Nginx Path')),
    cfg.StrOpt('wstun_endpoint',
            default='localhost',
            help=('Default Nginx Path'))
]

CONF = cfg.CONF
CONF.register_opts(nginx_opts, 'nginx')


def save_map(board, zone):
    fp = CONF.nginx.nginx_path + "/maps/map_" + board
    with open(fp, "w") as text_file:
        text_file.write("~" + board + "." + zone + " " + board + ";")


def save_upstream(board, https_port):
    fp = CONF.nginx.nginx_path + "/upstreams/upstream_" + board
    string = '''upstream {0} {{
    server {2}:{1} max_fails=3 fail_timeout=10s;
    }}
    '''.format(board, https_port, CONF.nginx.wstun_endpoint )

    with open(fp, "w") as text_file:
        text_file.write("%s" % string)


def save_server(board, http_port, zone):
    fp = CONF.nginx.nginx_path + "/servers/" + board
    string = '''server {{
    listen              80;
    server_name         .{0}.{2};

    location / {{
        proxy_pass http://{3}:{1};
    }}
    }}
    '''.format(board, http_port, zone, CONF.nginx.wstun_endpoint)

    with open(fp, "w") as text_file:
        text_file.write("%s" % string)


def remove(board):
    call(["rm",
          CONF.nginx.nginx_path + "/servers/" + board,
          CONF.nginx.nginx_path + "/upstreams/upstream_" + board,
          CONF.nginx.nginx_path + "/maps/map_" + board
          ])


def string_redirect(board, zone, dns=None):
    if not dns:
        host = "%s.%s" % (board, zone)
    else:
        host = "%s.%s.%s" % (dns, board, zone)
    string = "if ($host = %s) { return 301 https://$host$request_uri; }\n" % (
        host)
    return string


def insert_entry(line, lines):
    try:
        lines.index(line)
    except Exception:
        lines.insert(4, line)
    return lines


def remove_entry(line, lines):
    try:
        lines.remove(line)
    except Exception:
        pass
    return lines


def save_conf(f_conf, lines):
    f = open(f_conf, "w")
    lines = "".join(lines)
    f.write(lines)
    f.close()


class ProxyManager(Proxy):

    def __init__(self):
        super(ProxyManager, self).__init__("nginx")

    def reload_proxy(self, ctx):
        call(["nginx", "-s", "reload"])

    def enable_webservice(self, ctx, board, https_port, http_port, zone):
        LOG.debug(
            'Enabling WebService with ports  %s for http and %s for https '
            'on board %s', http_port, https_port, board)
        save_map(board, zone)
        save_upstream(board, https_port)
        save_server(board, http_port, zone)

    def disable_webservice(self, ctx, board):
        LOG.debug('Disabling WebService on board %s',
                  board)
        remove(board)

    def add_redirect(self, ctx, board_dns, zone, dns=None):
        line = string_redirect(board_dns, zone, dns)
        path = CONF.nginx.nginx_path + "/servers/" + board_dns
        LOG.debug('Adding redirect %s on %s', line, path)

        f = open(str(CONF.nginx.nginx_path + "/servers/" + board_dns), "r")
        lines = f.readlines()
        f.close()
        lines = insert_entry(line, lines)
        save_conf(path, lines)

    def remove_redirect(self, ctx, board_dns, zone, dns=None):
        path = CONF.nginx.nginx_path + "/servers/" + board_dns
        line = string_redirect(board_dns, zone, dns)
        LOG.debug('Removing redirect  %s on %s', line, path)

        f = open(path, "r")
        lines = f.readlines()
        f.close()
        lines = remove_entry(line, lines)
        save_conf(path, lines)
