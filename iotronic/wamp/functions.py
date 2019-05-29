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

from datetime import datetime
from iotronic.common import rpc
from iotronic.common import states
from iotronic.conductor import rpcapi
from iotronic import objects
from iotronic.wamp import wampmessage as wm
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


def wamp_alive(board_uuid, board_name):
    LOG.debug("Alive board: %s (%s)", board_uuid, board_name)
    return "Iotronic alive @ " + datetime.now().strftime(
        '%Y-%m-%dT%H:%M:%S.%f')


# to be removed
def alive():
    LOG.debug("Alive")
    return "Iotronic alive @ " + datetime.now().strftime(
        '%Y-%m-%dT%H:%M:%S.%f')


def update_sessions(session_list, agent):
    session_list = set(session_list)
    list_from_db = objects.SessionWP.valid_list(ctxt, agent)
    list_db = set([int(elem.session_id) for elem in list_from_db])
    LOG.debug('Wamp session list: %s', session_list)
    LOG.debug('DB session list: %s', list_db)

    if session_list == list_db:
        LOG.debug('Sessions on the database are updated.')
        return

    # list of board not connected anymore
    old_connected = list_db.difference(session_list)

    LOG.debug('no more valid session list: %s', old_connected)

    for elem in old_connected:
        old_session = objects.SessionWP.get(ctxt, elem)
        if old_session.valid:
            old_session.valid = False
            old_session.save()
            board = objects.Board.get_by_uuid(ctxt, old_session.board_uuid)
            board.status = states.OFFLINE
            board.save()
            LOG.debug('Session updated. Board %s is now  %s', board.uuid,
                      states.OFFLINE)

    if old_connected:
        LOG.warning('Some boards have been updated: status offline')

    # list of board still connected
    keep_connected = list_db.intersection(session_list)
    LOG.debug('still valid session list: %s', keep_connected)

    for elem in keep_connected:
        for x in list_from_db:
            if x.session_id == str(elem):
                LOG.debug('%s need to be restored.', x.board_uuid)
                break
    if keep_connected:
        LOG.warning('Some boards need to be restored.')


def board_on_leave(session_id):
    LOG.debug('A board with %s disconnectd', session_id)
    try:
        old_session = objects.SessionWP.get(ctxt, session_id)

        if old_session.valid:
            old_session.valid = False
            old_session.save()
            board = objects.Board.get_by_uuid(ctxt, old_session.board_uuid)
            board.status = states.OFFLINE
            board.save()
            LOG.debug('Session updated. Board %s is now  %s', board.uuid,
                      states.OFFLINE)
            return

        LOG.debug('Session %s already set to not valid', session_id)
    except Exception:
        LOG.debug('session %s not found', session_id)


def connection(uuid, session, info=None):
    LOG.debug('Received registration from %s with session %s',
              uuid, session)
    try:
        board = objects.Board.get_by_uuid(ctxt, uuid)
    except Exception as exc:
        msg = exc.message % {'board': uuid}
        LOG.error(msg)
        return wm.WampError(msg).serialize()
    try:
        old_ses = objects.SessionWP(ctxt)
        old_ses = old_ses.get_session_by_board_uuid(ctxt, board.uuid,
                                                    valid=True)
        old_ses.valid = False
        old_ses.save()
        LOG.debug('old session for %s found: %s', board.uuid,
                  old_ses.session_id)

    except Exception:
        LOG.debug('valid session for %s not found', board.uuid)

    session_data = {'board_id': board.id,
                    'board_uuid': board.uuid,
                    'session_id': session}
    session = objects.SessionWP(ctxt, **session_data)
    session.create()
    LOG.debug('new session for %s saved %s', board.uuid,
              session.session_id)
    board.status = states.ONLINE

    if info:
        LOG.debug('board infos %s', info)
        if 'lr_version' in info:
            if board.lr_version != info['lr_version']:
                board.lr_version = info['lr_version']
        if 'connectivity' in info:
            board.connectivity = info['connectivity']
        if 'mac_addr' in info:
            board.connectivity = {"mac_addr": info['mac_addr']}

    board.save()
    LOG.info('Board %s (%s) is now  %s', board.uuid,
             board.name, states.ONLINE)

    return wm.WampSuccess('').serialize()


def registration(code, session):
    return c.registration(ctxt, code, session)


def board_on_join(session_id):
    LOG.debug('A board with %s joined', session_id['session'])


def notify_result(board_uuid, wampmessage):
    wmsg = wm.deserialize(wampmessage)
    LOG.info('Board %s completed the its request %s with result: %s',
             board_uuid, wmsg.req_id, wmsg.result)

    res = objects.Result.get(ctxt, board_uuid, wmsg.req_id)
    res.result = wmsg.result
    res.message = wmsg.message
    res.save()

    filter = {"result": objects.result.RUNNING,
              "request_uuid": wmsg.req_id}

    list_result = objects.Result.get_results_list(ctxt,
                                                  filter)
    if len(list_result) == 0:
        req = objects.Request.get_by_uuid(ctxt, wmsg.req_id)
        req.status = objects.request.COMPLETED
        req.save()
        if req.main_request_uuid:
            mreq = objects.Request.get_by_uuid(ctxt, req.main_request_uuid)
            mreq.pending_requests = mreq.pending_requests - 1
            if mreq.pending_requests == 0:
                mreq.status = objects.request.COMPLETED
            mreq.save()

    return wm.WampSuccess('notification_received').serialize()
