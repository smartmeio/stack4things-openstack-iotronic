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


try:
    # allow iotronic api to run also with python3
    import _pickle as cpickle
except Exception:
    # allow iotronic api to run also with python2.7
    import pickle as cpickle

import random
import socket
import json


from oslo_config import cfg
from oslo_log import log as logging
import oslo_messaging

from iotronic import objects
from iotronic.common import exception, designate
from iotronic.common import neutron
from iotronic.common import states
from iotronic.conductor.provisioner import Provisioner
from iotronic.objects import base as objects_base
from iotronic.wamp import wampmessage as wm

LOG = logging.getLogger(__name__)

serializer = objects_base.IotronicObjectSerializer()

Port = list()

SERVICE_PORT_LIST = []



def versionCompare(v1, v2):
    """Method to compare two versions.
    Return 1 if v2 is smaller,
    -1 if v1 is smaller,
    0 if equal
    """

    if "freedom" in v1:
        return 1
    
    else:

        v1_list = v1.split(".")[:3]
        v2_list = v2.split(".")[:3]
        i = 0
        while (i < len(v1_list)):

            # v2 > v1
            if int(v2_list[i]) > int(v1_list[i]):
                return -1
            # v1 > v1
            if int(v1_list[i]) > int(v2_list[i]):
                return 1
            i += 1
        # v2 == v1
        return 0


def new_req(ctx, board, type, action, main_req=None, pending_requests=0):
    req_data = {
        'destination_uuid': board.uuid,
        'type': type,
        'status': objects.request.PENDING,
        'action': action,
        'project': board.project,
        'pending_requests': pending_requests
    }
    if main_req:
        req_data['main_request_uuid'] = main_req
    req = objects.Request(ctx, **req_data)
    req.create()
    return req


def new_res(ctx, board, req_uuid):
    res_data = {
        'board_uuid': board.uuid,
        'request_uuid': req_uuid,
        'result': objects.result.RUNNING,
        'message': ""
    }

    res = objects.Result(ctx, **res_data)
    res.create()
    return res


def get_best_agent(ctx):
    agents = objects.WampAgent.list(ctx, filters={'online': True})
    LOG.debug('found %d Agent(s).', len(agents))
    agent = random.choice(agents)
    LOG.debug('Selected agent: %s', agent.hostname)
    return agent.hostname


def random_public_port(ctx=None):
    global SERVICE_PORT_LIST
    if not SERVICE_PORT_LIST:
        # empty, create a cache list
        min = cfg.CONF.conductor.service_port_min + 1
        max = cfg.CONF.conductor.service_port_max - 1
        LOG.debug('recreate service port list cache: min %i max %i', min, max)
        full_list = (range(min, max))
        exp_list = objects.ExposedService.get_all_ports(ctx)
        SERVICE_PORT_LIST = list(set(full_list) - set(exp_list))

    if len(SERVICE_PORT_LIST) == 0:
        LOG.warning('No more ports available')
        return None
    else:
        num = random.choice(SERVICE_PORT_LIST)
        SERVICE_PORT_LIST.remove(num)
    return num


def manage_result(res, wamp_rpc_call, board_uuid):
    if res.result == wm.SUCCESS:
        return res.message
    elif res.result == wm.WARNING:
        LOG.warning('Warning in the execution of %s on %s', wamp_rpc_call,
                    board_uuid)
        return res.message
    elif res.result == wm.ERROR:
        LOG.error('Error in the execution of %s on %s: %s', wamp_rpc_call,
                  board_uuid, res.message)
        raise exception.ErrorExecutionOnBoard(call=wamp_rpc_call,
                                              board=board_uuid,
                                              error=res.message)
    return res.message


def create_record_dns_webservice(ctx, board, webs_name, board_dns, zone):
    agent = objects.WampAgent.get_by_hostname(ctx, board.agent)
    wsurl = agent.wsurl
    w_host = wsurl.split("//")[1].split(":")[0]
    ip = socket.gethostbyname(w_host)

    LOG.debug('Create dns record  %s for board %s',
              webs_name + "." + board_dns + "." + zone,
              board.uuid)
    LOG.debug('using  %s %s %s', webs_name + "." + board_dns,
              ip, zone)

    # CHECK IF DNS EXISTS
    designate.create_record(webs_name + "." + board_dns, ip,
                            zone)


def create_record_dns(ctx, board, board_dns, zone):
    agent = objects.WampAgent.get_by_hostname(ctx, board.agent)
    wsurl = agent.wsurl
    w_host = wsurl.split("//")[1].split(":")[0]
    ip = socket.gethostbyname(w_host)

    LOG.debug('Create dns record  %s for board %s',
              board_dns + "." + zone,
              board.uuid)
    LOG.debug('using %s %s %s', board_dns,
              ip, zone)

    # CHECK IF DNS EXISTS
    designate.create_record(board_dns, ip, zone)

    LOG.debug('Configure Web Proxy on WampAgent %s (%s) for board %s',
              board.agent, ip, board.uuid)


class ConductorEndpoint(object):
    def __init__(self, ragent):
        transport = oslo_messaging.get_transport(cfg.CONF)
        self.target = oslo_messaging.Target()

        self.wamp_agent_client = oslo_messaging.RPCClient(transport,
                                                          self.target)
        self.wamp_agent_client = self.wamp_agent_client.prepare(timeout=120,
                                                                topic='s4t')
        self.ragent = ragent

    def echo(self, ctx, data):
        LOG.info("ECHO: %s" % data)
        return data

    def registration(self, ctx, code, session_num):
        LOG.debug('Received registration from %s with session %s',
                  code, session_num)
        try:
            board = objects.Board.get_by_code(ctx, code)

        except Exception as exc:
            msg = exc.message % {'board': code}
            LOG.error(msg)
            return wm.WampError(msg).serialize()

        try:
            old_ses = objects.SessionWP(ctx)
            old_ses = old_ses.get_session_by_board_uuid(ctx, board.uuid,
                                                        valid=True)
            old_ses.valid = False
            old_ses.save()

        except Exception:
            LOG.debug('valid session for %s not found', board.uuid)

        session_data = {'board_id': board.id,
                        'board_uuid': board.uuid,
                        'session_id': session_num}
        session = objects.SessionWP(ctx, **session_data)
        session.create()

        if not board.status == states.REGISTERED:
            msg = "board with code %(board)s " \
                  "already registered" % {'board': code}
            LOG.warning((msg))
            board.status = states.OFFLINE
            board.save()
            LOG.debug('sending this conf %s', board.config)
            wmessage = wm.WampSuccess(board.config)
            return wmessage.serialize()

        board.agent = get_best_agent(ctx)
        agent = objects.WampAgent.get_by_hostname(ctx, board.agent)

        prov = Provisioner(board)
        prov.conf_registration_agent(self.ragent.wsurl)

        prov.conf_main_agent(agent.wsurl)
        loc = objects.Location.list_by_board_uuid(ctx, board.uuid)[0]
        prov.conf_location(loc)
        board.config = prov.get_config()

        board.status = states.OFFLINE
        board.save()

        LOG.debug('sending this conf %s', board.config)

        wmessage = wm.WampSuccess(board.config)
        return wmessage.serialize()

    def destroy_board(self, ctx, board_id):
        LOG.info('Destroying board with id %s',
                 board_id)
        board = objects.Board.get_by_uuid(ctx, board_id)
        result = None
        
        if board.is_online():

            try:
                result = self.execute_on_board(ctx,
                                               board_id,
                                               'DeviceFactoryReset',
                                               ())
            except exception:
                return exception

        exposed_list = objects.ExposedService.get_by_board_uuid(ctx,
                                                                board_id)

        LOG.debug('starting the wamp client')
        cctx = self.wamp_agent_client.prepare(server=board.agent)

        LOG.debug('Service to remove from allowlist:')
        LOG.debug(exposed_list)                                                        

        for exposed in exposed_list:
            LOG.debug(exposed.public_port)  
            cctx.call(ctx, 'remove_from_allowlist',
                            device=board_id,
                            port=exposed.public_port)
        
        board.destroy()

        if result:
            result = manage_result(result, 'destroyBoard', board_id)
            LOG.debug(result)
            return result
        return

    def update_board(self, ctx, board_obj):
        board = serializer.deserialize_entity(ctx, board_obj)
        LOG.debug('Updating board %s', board.name)
        board.save()
        return serializer.serialize_entity(ctx, board)

    def create_board(self, ctx, board_obj, location_obj):

        new_board = serializer.deserialize_entity(ctx, board_obj)
        LOG.debug('Creating board %s', new_board.name)

        board_exists = objects.Board.exists_by_name(ctx, new_board.name)
        #print(board_exists)

        if board_exists:
            raise exception.BoardNameAlreadyExists(name=new_board.name)
        else:
            new_location = serializer.deserialize_entity(ctx, location_obj)
            new_board.create()
            new_location.board_id = new_board.id
            new_location.create()

            return serializer.serialize_entity(ctx, new_board)

    def execute_on_board(self, ctx, board_uuid, wamp_rpc_call, wamp_rpc_args,
                         main_req=None):
        LOG.debug('Executing \"%s\" on the board: %s (main_req %s)',
                  wamp_rpc_call, board_uuid, main_req)

        board = objects.Board.get_by_uuid(ctx, board_uuid)
        # session should be taken from board, not from the object

        session = objects.SessionWP.get_session_by_board_uuid(ctx, board_uuid)
        full_wamp_call = 'iotronic.' + \
                         session.session_id + "." + \
                         board.uuid + "." + wamp_rpc_call

        if not board.is_online():
            raise exception.BoardNotConnected(board=board.uuid)

        req = new_req(ctx, board, objects.request.BOARD, wamp_rpc_call,
                      main_req)
        LOG.info(" - exec_request: " + str(req.uuid))

        res = new_res(ctx, board, req.uuid)

        cctx = self.wamp_agent_client.prepare(server=board.agent)

        # for previous LR version (to be removed asap)

        if (versionCompare(board.lr_version, "0.4.9") == -1):

            response = cctx.call(ctx, 's4t_invoke_wamp',
                                 wamp_rpc_call=full_wamp_call,
                                 data=wamp_rpc_args)
        else:
            response = cctx.call(ctx, 's4t_invoke_wamp',
                                 wamp_rpc_call=full_wamp_call,
                                 req=req,
                                 data=wamp_rpc_args)

        response = wm.deserialize(response)

        if (response.result != wm.RUNNING):
            res.result = response.result
            res.message = response.message
            res.save()
            req.status = objects.request.COMPLETED
            req.save()

            if req.main_request_uuid:
                mreq = objects.Request.get_by_uuid(ctx, req.main_request_uuid)
                mreq.pending_requests = mreq.pending_requests - 1
                if mreq.pending_requests == 0:
                    mreq.status = objects.request.COMPLETED
                mreq.save()

        return response

    def action_board(self, ctx, board_uuid, action, params):

        LOG.info('Calling action %s, into the board %s with params %s',
                 action, board_uuid, params)

        board = objects.Board.get(ctx, board_uuid)
        if not board.is_online():
            raise exception.BoardNotConnected(board=board.uuid)
        
        objects.board.is_valid_action(action)

        try:
            result = self.execute_on_board(ctx, board_uuid, action,
                                           (params,))
        except exception:
            return exception

        result = manage_result(result, action, board_uuid)
        LOG.debug(result)
        return result

    def destroy_plugin(self, ctx, plugin_id):
        LOG.info('Destroying plugin with id %s',
                 plugin_id)
        plugin = objects.Plugin.get_by_uuid(ctx, plugin_id)
        plugin.destroy()
        return

    def update_plugin(self, ctx, plugin_obj):
        plugin = serializer.deserialize_entity(ctx, plugin_obj)
        LOG.debug('Updating plugin %s', plugin.name)
        plugin.save()
        return serializer.serialize_entity(ctx, plugin)

    def create_plugin(self, ctx, plugin_obj):
        new_plugin = serializer.deserialize_entity(ctx, plugin_obj)
        LOG.debug('Creating plugin %s',
                  new_plugin.name)
        new_plugin.code = cpickle.dumps(new_plugin.code, 0).decode()
        new_plugin.create()
        return serializer.serialize_entity(ctx, new_plugin)

    def inject_plugin(self, ctx, plugin_uuid, board_uuid, onboot):
        LOG.info('Injecting plugin with id %s into the board %s',
                 plugin_uuid, board_uuid)

        plugin = objects.Plugin.get(ctx, plugin_uuid)
        try:
            result = self.execute_on_board(ctx,
                                           board_uuid,
                                           'PluginInject',
                                           (plugin, onboot))
        except exception:
            return exception

        injection = None
        try:
            injection = objects.InjectionPlugin.get(ctx,
                                                    board_uuid,
                                                    plugin_uuid)
        except Exception:
            pass
        if injection:
            injection.status = 'updated'
            injection.save()
        else:
            inj_data = {
                'board_uuid': board_uuid,
                'plugin_uuid': plugin_uuid,
                'onboot': onboot,
                'status': 'injected'
            }
            injection = objects.InjectionPlugin(ctx, **inj_data)
            injection.create()

        result = manage_result(result, 'PluginInject', board_uuid)
        LOG.debug(result)

        return result

    def remove_plugin(self, ctx, plugin_uuid, board_uuid):
        LOG.info('Removing plugin with id %s into the board %s',
                 plugin_uuid, board_uuid)

        plugin = objects.Plugin.get_by_uuid(ctx, plugin_uuid)

        injection = objects.InjectionPlugin.get(ctx, board_uuid, plugin_uuid)

        try:
            result = self.execute_on_board(ctx, board_uuid, 'PluginRemove',
                                           (plugin.uuid,))
        except exception:
            return exception
        result = manage_result(result, 'PluginRemove', board_uuid)
        LOG.debug(result)
        injection.destroy()
        return result

    def action_plugin(self, ctx, plugin_uuid, board_uuid, action, params):
        LOG.info('Calling plugin with id %s into the board %s with params %s',
                 plugin_uuid, board_uuid, params)
        plugin = objects.Plugin.get(ctx, plugin_uuid)
        objects.plugin.is_valid_action(action)

        try:
            if objects.plugin.want_params(action):
                result = self.execute_on_board(ctx, board_uuid, action,
                                               (plugin.uuid, params))
            else:
                result = self.execute_on_board(ctx, board_uuid, action,
                                               (plugin.uuid,))
        except exception:
            return exception
        result = manage_result(result, action, board_uuid)
        LOG.debug(result)
        return result

    def create_service(self, ctx, service_obj):
        new_service = serializer.deserialize_entity(ctx, service_obj)
        LOG.debug('Creating service %s',
                  new_service.name)
        new_service.create()
        return serializer.serialize_entity(ctx, new_service)

    def destroy_service(self, ctx, service_id):
        LOG.info('Destroying service with id %s',
                 service_id)
        service = objects.Service.get_by_uuid(ctx, service_id)
        service.destroy()
        return

    def update_service(self, ctx, service_obj):
        service = serializer.deserialize_entity(ctx, service_obj)
        LOG.debug('Updating service %s', service.name)
        service.save()
        return serializer.serialize_entity(ctx, service)

    def action_service(self, ctx, service_uuid, board_uuid, action):
        service = objects.Service.get(ctx, service_uuid)
        objects.service.is_valid_action(action)

        board = objects.Board.get_by_uuid(ctx, board_uuid)
        if not board.is_online():
            raise exception.BoardNotConnected(board=board.uuid)

        if action == "ServiceEnable":
            LOG.info('Enabling service with id %s into the board %s',
                     service_uuid, board_uuid)
            try:
                objects.ExposedService.get(ctx,
                                           board_uuid,
                                           service_uuid)
                return exception.ServiceAlreadyExposed(uuid=service_uuid)
            except Exception:

                public_port = random_public_port()

                if not public_port:
                    return exception.NotEnoughPortForService()

                # Add into service allow list
                #if cfg.CONF.conductor.service_allow_list:
                #    addin_allowlist(board_uuid, public_port)
                LOG.debug('starting the wamp client')
                cctx = self.wamp_agent_client.prepare(server=board.agent)
                cctx.call(ctx, 'addin_allowlist',
                            device=board_uuid,
                            port=public_port)



                res = self.execute_on_board(ctx, board_uuid, action,
                                            (service, public_port))
                result = manage_result(res, action, board_uuid)

                exp_data = {
                    'board_uuid': board_uuid,
                    'service_uuid': service_uuid,
                    'public_port': public_port,
                }
                exposed = objects.ExposedService(ctx, **exp_data)
                exposed.create()

                LOG.debug(result)
                return result

        elif action == "ServiceDisable":
            LOG.info('Disabling service with id %s into the board %s',
                     service_uuid, board_uuid)
            exposed = objects.ExposedService.get(ctx,
                                                 board_uuid,
                                                 service_uuid)

            res = self.execute_on_board(ctx, board_uuid, action,
                                        (service,))

            result = manage_result(res, action, board_uuid)
            LOG.debug(res.message)
            global SERVICE_PORT_LIST
            try:
                SERVICE_PORT_LIST.append(exposed.public_port)
            except exception:
                pass
            exposed.destroy()


            # Remove from service allow list
            #if cfg.CONF.conductor.service_allow_list:
                #remove_from_allowlist(board_uuid, exposed.public_port)
            LOG.debug('starting the wamp client')
            cctx = self.wamp_agent_client.prepare(server=board.agent)
            cctx.call(ctx, 'remove_from_allowlist',
                            device=board_uuid,
                            port=exposed.public_port)


            return result

        elif action == "ServiceRestore":
            LOG.info('Restoring service with id %s into the board %s',
                     service_uuid, board_uuid)
            exposed = objects.ExposedService.get(ctx, board_uuid,
                                                 service_uuid)

            res = self.execute_on_board(ctx, board_uuid, action,
                                        (service, exposed.public_port))

            result = manage_result(res, action, board_uuid)
            LOG.debug(result)
            return result

    def restore_services_on_board(self, ctx, board_uuid):
        LOG.info('Restoring the services into the board %s',
                 board_uuid)
        exposed_list = objects.ExposedService.get_by_board_uuid(ctx,
                                                                board_uuid)

        for exposed in exposed_list:
            service = objects.Service.get_by_uuid(ctx, exposed.service_uuid)
            self.execute_on_board(ctx, board_uuid, "ServiceRestore",
                                  (service, exposed.public_port))

        return 0

    def status_services_on_board(self, ctx, board_uuid):
        LOG.info('Getting services status into devide %s',
                 board_uuid)

        action = "ServicesStatus"

        board = objects.Board.get(ctx, board_uuid)
        if not board.is_online():
            raise exception.BoardNotConnected(board=board.uuid)

        try:
            result = self.execute_on_board(ctx, board_uuid, action, ())
        except exception:
            return exception

        result = manage_result(result, action, board_uuid)
        LOG.debug(result)
        return result

    def create_port_on_board(self, ctx, board_uuid, network_uuid,
                             subnet_uuid, security_groups=None):

        LOG.info('Creation of a port on the board %s in the network',
                 board_uuid)

        board = objects.Board.get_by_uuid(ctx, board_uuid)
        if not board.is_online():
            raise exception.BoardNotConnected(board=board.uuid)
        port_iotronic = objects.Port(ctx)

        subnet_info = neutron.subnet_info(subnet_uuid)
        cidr = str(subnet_info['subnet']['cidr'])
        slash = cidr.split("/", 1)[1]
        try:

            port = neutron.add_port_to_network(board, network_uuid,
                                               subnet_uuid, security_groups)
            p = str(port['port']['id'])

            port_socat = random.randint(10000, 20000)

            i = 0
            while i < len(Port):
                if Port[i] == port_socat:
                    i = 0
                    port_socat = random.randint(10000, 20000)
                i += 1

            Port.insert(0, port_socat)
            r_tcp_port = str(port_socat)

            try:
                LOG.info('Creation of the VIF on the board')
                self.execute_on_board(ctx, board_uuid, "Create_VIF",
                                      (r_tcp_port,))

                try:
                    LOG.debug('starting the wamp client')
                    cctx = self.wamp_agent_client.prepare(server=board.agent)
                    cctx.call(ctx, 'create_tap_interface',
                              port_uuid=p,
                              tcp_port=r_tcp_port)

                    try:
                        LOG.info('Updating the DB')
                        VIF = str("iotronic" + str(r_tcp_port))
                        port_iotronic.VIF_name = VIF
                        port_iotronic.uuid = port['port']['id']
                        port_iotronic.MAC_add = port['port']['mac_address']
                        port_iotronic.board_uuid = str(board_uuid)
                        port_iotronic.network = \
                            port['port']['fixed_ips'][0]['subnet_id']
                        port_iotronic.ip = \
                            port['port']['fixed_ips'][0]['ip_address']
                        port_iotronic.create()

                        try:
                            LOG.debug('Configuration of the VIF')
                            self.execute_on_board(ctx, board_uuid,
                                                  "Configure_VIF",
                                                  (port_iotronic, slash,))
                            return port_iotronic

                        except Exception:
                            LOG.error("Error while configuring the VIF")

                    except Exception as e:
                        LOG.error('Error while updating the DB :' + str(e))

                except Exception:
                    LOG.error('wamp client error')

            except Exception:
                LOG.error('Error while creating the VIF')

        except Exception as e:
            LOG.error(str(e))

    def remove_VIF_from_board(self, ctx, board_uuid, port_uuid):

        LOG.info('removing the port %s from board %s',
                 port_uuid, board_uuid)

        board = objects.Board.get_by_uuid(ctx, board_uuid)
        port = objects.Port.get_by_uuid(ctx, port_uuid)
        VIF_name = str(port.VIF_name)

        try:

            self.execute_on_board(ctx, board_uuid, "Remove_VIF", (VIF_name,))
            port_num = int(VIF_name[8:])
            global Port
            Port.remove(port_num)
            try:
                LOG.info("Removing the port from Neutron "
                         "and Iotronic databases")
                neutron.delete_port(board.agent, port_uuid)
                LOG.info("Port removed from Neutron DB")
                port.destroy()
                LOG.info("Port removed from Iotronic DB")

                return port

            except Exception as e:
                LOG.error(str(e))

        except Exception as e:
            LOG.error(str(e))

    def create_fleet(self, ctx, fleet_obj):
        new_fleet = serializer.deserialize_entity(ctx, fleet_obj)
        LOG.debug('Creating fleet %s',
                  new_fleet.name)
        new_fleet.create()
        return serializer.serialize_entity(ctx, new_fleet)

    def destroy_fleet(self, ctx, fleet_id):
        LOG.info('Destroying fleet with id %s',
                 fleet_id)
        fleet = objects.Fleet.get_by_uuid(ctx, fleet_id)
        fleet.destroy()
        return

    def update_fleet(self, ctx, fleet_obj):
        fleet = serializer.deserialize_entity(ctx, fleet_obj)
        LOG.debug('Updating fleet %s', fleet.name)
        fleet.save()
        return serializer.serialize_entity(ctx, fleet)

    def create_webservice(self, ctx, webservice_obj):
        newwbs = serializer.deserialize_entity(ctx, webservice_obj)
        LOG.debug('Creating webservice %s', newwbs.name)

        board = objects.Board.get_by_uuid(ctx, newwbs.board_uuid)
        if not board.is_online():
            raise exception.BoardNotConnected(board=board.uuid)

        LOG.info(" - expose "+str(newwbs.name)+" in " + str(board.name) + " ["+str(newwbs.board_uuid)+"]")
        list_webs = objects.Webservice.list(
            ctx, 
            filters={'board_uuid': newwbs.board_uuid}
        )
        
        dns_check=True
        webs_found=None

        for webs in list_webs:
            wboard = objects.Board.get(ctx, webs.board_uuid)
            LOG.info(" --> " + str(webs.name) + ", " + str(wboard.name) + ", " + str(webs.board_uuid) + ", " + str(webs.port) )
            if (str(newwbs.board_uuid) == str(webs.board_uuid)) and (newwbs.name == str(webs.name)):
                dns_check = False
                webs_found = webs
                break

        if dns_check:

            LOG.info("Webservice can be exposed!")

            en_webservice = objects.enabledwebservice. \
                EnabledWebservice.get_by_board_uuid(ctx,
                                                    newwbs.board_uuid)

            full_zone_domain = en_webservice.dns + "." + en_webservice.zone
            dns_domain = newwbs.name + "." + full_zone_domain

            create_record_dns_webservice(ctx, board, newwbs.name,
                                        en_webservice.dns,
                                        en_webservice.zone)

            LOG.debug('Creating webservice with full domain %s',
                    dns_domain)

            list_dns = full_zone_domain + ","
            for webs in list_webs:
                dname = webs.name + "." + full_zone_domain + ","
                list_dns = list_dns + dname

            list_dns = list_dns + dns_domain

            try:
                res = self.execute_on_board(ctx,
                                    newwbs.board_uuid,
                                    'ExposeWebservice',
                                    (full_zone_domain,
                                    dns_domain,
                                    newwbs.port,
                                    list_dns,))
            except exception:
                return exception

            cctx = self.wamp_agent_client.prepare(server=board.agent)
            cctx.call(ctx, 'add_redirect', board_dns=en_webservice.dns,
                    zone=en_webservice.zone, dns=newwbs.name)
            cctx.call(ctx, 'reload_proxy')

            newwbs.create()

            result = manage_result(res, "ExposeWebservice", board.uuid)
            LOG.info(result)
            #return result

            return serializer.serialize_entity(ctx, newwbs)

        else:

            mreq = new_req(ctx, board, objects.request.BOARD,
                "expose_webservice", pending_requests=0)
            LOG.info(" - request: " + str(mreq.uuid))

            
            
            msg="Webservice already exposed for this device!"
            w_msg = wm.WampWarning(msg, req_id=mreq.uuid)

            res = new_res(ctx, board, mreq.uuid) 
            res.result = w_msg.result
            res.message = w_msg.message
            res.save()

            mreq.status = objects.request.COMPLETED
            mreq.save()

            result = manage_result(w_msg, "ExposeWebservice", board.uuid)

            LOG.info(result)
            #return result
            return serializer.serialize_entity(ctx, webs_found)

    def destroy_webservice(self, ctx, webservice_id):
        LOG.info('Destroying webservice with id %s',
                 webservice_id)

        wbsrv = objects.Webservice.get_by_uuid(ctx, webservice_id)

        board = objects.Board.get_by_uuid(ctx, wbsrv.board_uuid)

        #if not board.is_online():
        #    raise exception.BoardNotConnected(board=board.uuid)

        en_webservice = objects.enabledwebservice. \
            EnabledWebservice.get_by_board_uuid(ctx,
                                                wbsrv.board_uuid)

        if board.is_online():

            full_zone_domain = en_webservice.dns + "." + en_webservice.zone
            dns_domain = wbsrv.name + "." + full_zone_domain

            list_webs = objects.Webservice.list(ctx,
                                                filters={
                                                    'board_uuid': wbsrv.board_uuid
                                                })

            list_dns = full_zone_domain + ","
            for webs in list_webs:
                if webs.name != wbsrv.name:
                    dname = webs.name + "." + full_zone_domain + ","
                    list_dns = list_dns + dname
            list_dns = list_dns[:-1]

            try:
                # result =
                self.execute_on_board(ctx,
                                    wbsrv.board_uuid,
                                    'UnexposeWebservice',
                                    (dns_domain, list_dns,))
            except exception:
                return exception

            if board.agent == None:
                raise exception.BoardInvalidStatus(uuid=board.uuid,
                                                status=board.status)

            cctx = self.wamp_agent_client.prepare(server=board.agent)
            cctx.call(ctx, 'remove_redirect', board_dns=en_webservice.dns,
                    zone=en_webservice.zone, dns=wbsrv.name)
            cctx.call(ctx, 'reload_proxy')

        wbsrv.destroy()
        designate.delete_record(wbsrv.name + "." + en_webservice.dns,
                                en_webservice.zone)

        return

    def enable_webservice(self, ctx, dns, zone, email, board_uuid):

        board = objects.Board.get_by_uuid(ctx, board_uuid)
        if not board.is_online():
            raise exception.BoardNotConnected(board=board.uuid)

        if board.agent == None:
            raise exception.BoardInvalidStatus(uuid=board.uuid,
                                               status=board.status)
        #print("DNS: " + str(dns))

        avl_webservice = objects.enabledwebservice.EnabledWebservice.checkDnsAvailable(ctx, dns)
        #print("Available: " + str(avl_webservice))

        LOG.info("Enabling Webservice module for device " + str(board.name) + " ["+board_uuid+"]")

        if avl_webservice:

            en_webservice = objects.enabledwebservice.EnabledWebservice.isWebserviceEnabled(ctx, board.uuid)

            if(en_webservice):

                mreq = new_req(ctx, board, objects.request.BOARD,
                    "enable_webservice", pending_requests=0)
                LOG.info(" - request: " + str(mreq.uuid))

                res = new_res(ctx, board, mreq.uuid) 

                en_webservice = objects.enabledwebservice.EnabledWebservice.get_by_board_uuid(ctx, board.uuid)

                LOG.info("Webservice and dns already enabled for this device:")
                full_zone_domain = en_webservice.dns + "." + en_webservice.zone

                LOG.info(" --> " + str(full_zone_domain))

                msg="Webservice and dns already enabled for this device!"
                w_msg = wm.WampWarning(msg, req_id=mreq.uuid)

                res.result = w_msg.result
                res.message = w_msg.message
                res.save()

                mreq.status = objects.request.COMPLETED
                mreq.save()

                result = manage_result(w_msg, "EnableWebservice", board.uuid)

                LOG.info(result)

                raise exception.EnabledWebserviceAlreadyExists(enabled_webservice=full_zone_domain, req=mreq.uuid)

                #return serializer.serialize_entity(ctx, en_webservice)


            else:
 
                mreq = new_req(ctx, board, objects.request.BOARD,
                            "enable_webservice", pending_requests=3)

                try:
                    create_record_dns(ctx, board, dns, zone)
                except exception:
                    return exception

                try:
                    en_webservice = objects.enabledwebservice. \
                        EnabledWebservice.get_by_board_uuid(ctx,
                                                            board.uuid)

                    LOG.debug('Webservice data already exists for board %s',
                            board.uuid)
                    https_port = en_webservice.https_port
                    http_port = en_webservice.http_port

                except Exception:

                    https_port = random_public_port()
                    http_port = random_public_port()
                    if not https_port or not http_port:
                        return exception.NotEnoughPortForService()

                    en_webservice = {
                        'board_uuid': board.uuid,
                        'http_port': http_port,
                        'https_port': https_port,
                        'dns': dns,
                        'zone': zone
                    }
                    en_webservice = objects.enabledwebservice.EnabledWebservice(
                        ctx, **en_webservice)

                    LOG.debug('Save webservice data %s for board %s', dns + "." + zone,
                            board.uuid)
                    en_webservice.create()

                LOG.debug('Open ports on WampAgent %s for http and %s for https '
                        'on board %s', http_port, https_port, board.uuid)

                service = objects.Service.get_by_name(ctx, 'webservice')


                LOG.debug('starting the wamp client')
                cctx = self.wamp_agent_client.prepare(server=board.agent)
                cctx.call(ctx, 'addin_allowlist',
                            device=board.uuid,
                            port=http_port)
                cctx.call(ctx, 'addin_allowlist',
                            device=board.uuid,
                            port=https_port)

                res = self.execute_on_board(ctx, board.uuid, "ServiceEnable",
                                            (service, http_port,), main_req=mreq.uuid)
                result = manage_result(res, "ServiceEnable", board.uuid)

                exp_data = {
                    'board_uuid': board_uuid,
                    'service_uuid': service.uuid,
                    'public_port': http_port,
                }
                exposed = objects.ExposedService(ctx, **exp_data)
                exposed.create()

                LOG.debug(result)

                service = objects.Service.get_by_name(ctx, 'webservice_ssl')





                res = self.execute_on_board(ctx, board.uuid, "ServiceEnable",
                                            (service, https_port,), main_req=mreq.uuid)
                result = manage_result(res, "ServiceEnable", board.uuid)

                exp_data = {
                    'board_uuid': board_uuid,
                    'service_uuid': service.uuid,
                    'public_port': https_port,
                }
                exposed = objects.ExposedService(ctx, **exp_data)
                exposed.create()

                LOG.debug(result)

                cctx = self.wamp_agent_client.prepare(server=board.agent)
                cctx.call(ctx, 'enable_webservice', board=dns,
                        https_port=https_port, http_port=http_port, zone=zone)
                cctx.call(ctx, 'reload_proxy')

                LOG.debug('Configure Web Proxy on Board %s with dns %s (email: %s) ',
                        board.uuid, dns, email)

                try:
                    self.execute_on_board(ctx,
                                        board.uuid,
                                        'EnableWebService',
                                        (dns + "." + zone, email,),
                                        main_req=mreq.uuid)
                except exception:
                    return exception

                cctx.call(ctx, 'add_redirect', board_dns=dns, zone=zone)
                cctx.call(ctx, 'reload_proxy')

                return serializer.serialize_entity(ctx, en_webservice)


        else:
            mreq = new_req(ctx, board, objects.request.BOARD,
                "enable_webservice", pending_requests=0)
            LOG.info(" - request: " + str(mreq.uuid))

            res = new_res(ctx, board, mreq.uuid) 

            msg="DNS already exists!"
            w_msg = wm.WampWarning(msg, req_id=mreq.uuid)

            res.result = w_msg.result
            res.message = w_msg.message
            res.save()

            mreq.status = objects.request.COMPLETED
            mreq.save()

            result = manage_result(w_msg, "EnableWebservice", board.uuid)

            LOG.info(" - result: " + str(result))
            
            raise exception.DnsWebserviceAlreadyExists(dns=dns, req=mreq.uuid)

    def disable_webservice(self, ctx, board_uuid):
        LOG.info('Disabling webservice on board id %s',
                 board_uuid)

        board = objects.Board.get_by_uuid(ctx, board_uuid)

        #if not board.is_online():
        #    raise exception.BoardNotConnected(board=board.uuid)

        if board.agent == None:
            raise exception.BoardInvalidStatus(uuid=board.uuid,
                                               status=board.status)

        mreq = new_req(ctx, board, objects.request.BOARD,
                       "disable_webservice", pending_requests=3)

        en_webservice = objects.enabledwebservice. \
            EnabledWebservice.get_by_board_uuid(ctx,
                                                board.uuid)

        https_port = en_webservice.https_port
        http_port = en_webservice.http_port

        LOG.debug('Disable Webservices ports %s for http and %s for https '
                  'on board %s', http_port, https_port, board.uuid)

        service = objects.Service.get_by_name(ctx, 'webservice')

        exposed = objects.ExposedService.get(ctx,
                                             board_uuid,
                                             service.uuid)

        if board.is_online():
            res = self.execute_on_board(ctx, board.uuid, "ServiceDisable",
                                    (service,), main_req=mreq.uuid)
            LOG.debug(res.message)

        exposed.destroy()

        service = objects.Service.get_by_name(ctx, 'webservice_ssl')

        exposed = objects.ExposedService.get(ctx,
                                             board_uuid,
                                             service.uuid)

        if board.is_online():
            res = self.execute_on_board(ctx, board.uuid, "ServiceDisable",
                                    (service,), main_req=mreq.uuid)
            LOG.debug(res.message)


        global SERVICE_PORT_LIST
        try:
            SERVICE_PORT_LIST.append(exposed.public_port)
        except exception:
            pass
        exposed.destroy()

        if board.is_online():
            try:
                self.execute_on_board(ctx,
                                    board.uuid,
                                    'DisableWebService',
                                    (),
                                    main_req=mreq.uuid)
            except exception:
                return exception

        webservice = objects.EnabledWebservice.get_by_board_uuid(
            ctx, board_uuid)

        LOG.debug('Remove dns record  %s  for board %s',
                  webservice.dns, board.uuid)

        designate.delete_record(webservice.dns, en_webservice.zone)

        if board.is_online():
            cctx = self.wamp_agent_client.prepare(server=board.agent)
            cctx.call(ctx, 'disable_webservice', board=webservice.dns)

            # cctx.call(ctx, 'remove_redirect', board_dns=en_webservice.dns,
            #          zone=en_webservice.zone)

            cctx.call(ctx, 'reload_proxy')

        
        LOG.debug('starting the wamp client')
        cctx = self.wamp_agent_client.prepare(server=board.agent)
        cctx.call(ctx, 'remove_from_allowlist',
                        device=board.uuid,
                        port=http_port)


        cctx.call(ctx, 'remove_from_allowlist',
                        device=board.uuid,
                        port=https_port)

        webservice.destroy()

        return

    def renew_webservice(self, ctx, board_uuid):

        board = objects.Board.get_by_uuid(ctx, board_uuid)
        if not board.is_online():
            raise exception.BoardNotConnected(board=board.uuid)

        if board.agent == None:
            raise exception.BoardInvalidStatus(uuid=board.uuid,
                                               status=board.status)

        LOG.info('Renewing certificates on device %s', board.uuid)

        en_webservice = objects.enabledwebservice.EnabledWebservice.isWebserviceEnabled(ctx, board.uuid)

        if(en_webservice):

            mreq = new_req(ctx, board, objects.request.BOARD,
                       "RenewWebservice", pending_requests=1)

            res = self.execute_on_board(ctx, board.uuid, "RenewWebservice", (), main_req=mreq.uuid )
            
        else:

            mreq = new_req(ctx, board, objects.request.BOARD,
                       "RenewWebservice", pending_requests=0)
            LOG.info(" - request: " + str(mreq.uuid))

            msg="Webservice module not enabled for this device!"
            w_msg = wm.WampWarning(msg, req_id=mreq.uuid)

            res = new_res(ctx, board, mreq.uuid) 
            res.result = w_msg.result
            res.message = w_msg.message
            res.save()

            mreq.status = objects.request.COMPLETED
            mreq.save()

            raise exception.EnabledWebserviceNotFound(enabled_webservice=board.uuid)
            

        result = manage_result(res, "RenewWebservice", board.uuid)
        LOG.info(" - " + str(result))

        return serializer.serialize_entity(ctx, en_webservice)
