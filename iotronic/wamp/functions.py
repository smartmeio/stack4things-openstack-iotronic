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

from iotronic.common import rpc
from iotronic.common import states
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


def board_on_leave(session_id):
    LOG.debug('A board with %s disconnectd', session_id)

    try:
        old_session = objects.SessionWP.get(ctxt, session_id)
        old_session.valid = False
        old_session.save()
        LOG.debug('Session %s deleted', session_id)
    except Exception:
        LOG.debug('session %s not found', session_id)

    board = objects.Board.get_by_uuid(ctxt, old_session.board_uuid)
    board.status = states.OFFLINE
    board.save()
    LOG.debug('Board %s is now  %s', old_session.uuid, states.OFFLINE)


def on_board_connect(board_uuid, session_id, msg):
    if msg == 'connection':
        try:
            board = objects.Board.get_by_uuid(ctxt, board_uuid)
            board.status = states.ONLINE
            session_data = {'board_id': board.id,
                            'board_uuid': board.uuid,
                            'session_id': session_id}
            session = objects.SessionWP(ctxt, **session_data)
            session.create()
            board.save()
            LOG.debug('Board %s is now  %s', board_uuid, states.ONLINE)
        except Exception:
            LOG.debug(Exception.message)


def connection(uuid, session):
    return c.connection(ctxt, uuid, session)


def registration(code, session):
    return c.registration(ctxt, code, session)


def board_on_join(session_id):
    LOG.debug('A board with %s joined', session_id['session'])
