# Copyright 2011 OpenStack LLC.
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

from iotronic.common import rpc
from iotronic.conductor import rpcapi
from iotronic import objects
from oslo_config import cfg
from oslo_log import log

LOG = log.getLogger(__name__)

CONF = cfg.CONF
CONF(project='iotronic')

rpc.init(CONF)

topic = 'iotronic.conductor_manager'
c = rpcapi.ConductorAPI(topic)


class cont(object):
    def to_dict(self):
        return {}


ctxt = cont()


def echo(data):
    LOG.info("ECHO: %s" % data)
    return data


def node_on_leave(session_id):
    LOG.debug('A node with %s disconnectd', session_id)
    try:
        old_session = objects.SessionWP({}).get_by_session_id({}, session_id)
        old_session.valid = False
        old_session.save()
        LOG.debug('Session %s deleted', session_id)
    except Exception:
        LOG.debug('session %s not found', session_id)


def registration_uuid(uuid, session):
    return c.registration_uuid(ctxt, uuid, session)


def registration(code, session):
    return c.registration(ctxt, code, session)


def node_on_join(session_id):
    LOG.debug('A node with %s joined', session_id)
