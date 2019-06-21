#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.


from iotronic.api.controllers import base
from iotronic.api.controllers import link
from iotronic.api.controllers.v1.board import BoardCollection
from iotronic.api.controllers.v1 import collection
from iotronic.api.controllers.v1 import types
from iotronic.api.controllers.v1 import utils as api_utils
from iotronic.api import expose
from iotronic.common import exception
from iotronic.common import policy
from iotronic import objects

import pecan
from pecan import rest
import wsme
from wsme import types as wtypes

_DEFAULT_RETURN_FIELDS = (
    'name', 'uuid', 'project', 'description', 'extra')

_DEFAULT_BOARDS_RETURN_FIELDS = ('name', 'code', 'status', 'uuid',
                                 'session', 'type', 'fleet', 'lr_version',
                                 'connectivity', 'agent', 'wstun_ip')


class Fleet(base.APIBase):
    """API representation of a fleet.

    """
    uuid = types.uuid
    name = wsme.wsattr(wtypes.text)
    project = types.uuid
    description = wsme.wsattr(wtypes.text)
    extra = types.jsontype

    links = wsme.wsattr([link.Link], readonly=True)

    def __init__(self, **kwargs):
        self.fields = []
        fields = list(objects.Fleet.fields)
        for k in fields:
            # Skip fields we do not expose.
            if not hasattr(self, k):
                continue
            self.fields.append(k)
            setattr(self, k, kwargs.get(k, wtypes.Unset))

    @staticmethod
    def _convert_with_links(fleet, url, fields=None):
        fleet_uuid = fleet.uuid
        if fields is not None:
            fleet.unset_fields_except(fields)

        fleet.links = [link.Link.make_link('self', url, 'fleets',
                                           fleet_uuid),
                       link.Link.make_link('bookmark', url, 'fleets',
                                           fleet_uuid, bookmark=True)
                       ]
        return fleet

    @classmethod
    def convert_with_links(cls, rpc_fleet, fields=None):
        fleet = Fleet(**rpc_fleet.as_dict())

        if fields is not None:
            api_utils.check_for_invalid_fields(fields, fleet.as_dict())

        return cls._convert_with_links(fleet, pecan.request.public_url,
                                       fields=fields)


class FleetCollection(collection.Collection):
    """API representation of a collection of fleets."""

    fleets = [Fleet]
    """A list containing fleets objects"""

    def __init__(self, **kwargs):
        self._type = 'fleets'

    @staticmethod
    def convert_with_links(fleets, limit, url=None, fields=None, **kwargs):
        collection = FleetCollection()
        collection.fleets = [Fleet.convert_with_links(n, fields=fields)
                             for n in fleets]
        collection.next = collection.get_next(limit, url=url, **kwargs)
        return collection


class FleetBoardsController(rest.RestController):
    def __init__(self, fleet_ident):
        self.fleet_ident = fleet_ident

    @expose.expose(BoardCollection, types.uuid, int, wtypes.text,
                   wtypes.text, types.listtype)
    def get_all(self, marker=None,
                limit=None, sort_key='id', sort_dir='asc',
                fields=None):
        """Retrieve a list of boards.

        :param marker: pagination marker for large data sets.
        :param limit: maximum number of resources to return in a single result.
                      This value cannot be larger than the value of max_limit
                      in the [api] section of the ironic configuration, or only
                      max_limit resources will be returned.
        :param sort_key: column to sort results by. Default: id.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.
        :param fields: Optional, a list with a specified set of fields
                       of the resource to be returned.
        """
        cdict = pecan.request.context.to_policy_values()
        policy.authorize('iot:board:get', cdict, cdict)

        if fields is None:
            fields = _DEFAULT_BOARDS_RETURN_FIELDS

        filters = {}
        filters['fleet'] = self.fleet_ident

        boards = objects.Board.list(pecan.request.context, limit, marker,
                                    sort_key=sort_key, sort_dir=sort_dir,
                                    filters=filters)

        parameters = {'sort_key': sort_key, 'sort_dir': sort_dir}

        return BoardCollection.convert_with_links(boards, limit,
                                                  fields=fields,
                                                  **parameters)


class FleetsController(rest.RestController):
    """REST controller for Fleets."""

    _subcontroller_map = {
        'boards': FleetBoardsController,
    }

    invalid_sort_key_list = ['extra', ]

    _custom_actions = {
        'detail': ['GET'],
    }

    @pecan.expose()
    def _lookup(self, ident, *remainder):
        try:
            ident = types.uuid_or_name.validate(ident)
        except exception.InvalidUuidOrName as e:
            pecan.abort('400', e.args[0])
        if not remainder:
            return

        subcontroller = self._subcontroller_map.get(remainder[0])
        if subcontroller:
            return subcontroller(fleet_ident=ident), remainder[1:]

    def _get_fleets_collection(self, marker, limit,
                               sort_key, sort_dir,
                               project=None,
                               fields=None):

        limit = api_utils.validate_limit(limit)
        sort_dir = api_utils.validate_sort_dir(sort_dir)

        marker_obj = None
        if marker:
            marker_obj = objects.Fleet.get_by_uuid(pecan.request.context,
                                                   marker)

        if sort_key in self.invalid_sort_key_list:
            raise exception.InvalidParameterValue(
                ("The sort_key value %(key)s is an invalid field for "
                 "sorting") % {'key': sort_key})

        filters = {}

        if project:
            if pecan.request.context.is_admin:
                filters['project_id'] = project
        fleets = objects.Fleet.list(pecan.request.context, limit,
                                    marker_obj,
                                    sort_key=sort_key, sort_dir=sort_dir,
                                    filters=filters)

        parameters = {'sort_key': sort_key, 'sort_dir': sort_dir}

        return FleetCollection.convert_with_links(fleets, limit,
                                                  fields=fields,
                                                  **parameters)

    @expose.expose(Fleet, types.uuid_or_name, types.listtype)
    def get_one(self, fleet_ident, fields=None):
        """Retrieve information about the given fleet.

        :param fleet_ident: UUID or logical name of a fleet.
        :param fields: Optional, a list with a specified set of fields
            of the resource to be returned.
        """

        rpc_fleet = api_utils.get_rpc_fleet(fleet_ident)
        cdict = pecan.request.context.to_policy_values()
        cdict['project_id'] = rpc_fleet.project
        policy.authorize('iot:fleet:get_one', cdict, cdict)

        return Fleet.convert_with_links(rpc_fleet, fields=fields)

    @expose.expose(FleetCollection, types.uuid, int, wtypes.text,
                   wtypes.text, types.listtype, types.boolean, types.boolean)
    def get_all(self, marker=None,
                limit=None, sort_key='id', sort_dir='asc',
                fields=None):
        """Retrieve a list of fleets.

        :param marker: pagination marker for large data sets.
        :param limit: maximum number of resources to return in a single result.
                      This value cannot be larger than the value of max_limit
                      in the [api] section of the ironic configuration, or only
                      max_limit resources will be returned.
        :param sort_key: column to sort results by. Default: id.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.
        :param with_public: Optional boolean to get also public pluings.
        :param all_fleets: Optional boolean to get all the pluings.
                            Only for the admin
        :param fields: Optional, a list with a specified set of fields
                       of the resource to be returned.
        """
        cdict = pecan.request.context.to_policy_values()
        policy.authorize('iot:fleet:get', cdict, cdict)

        if fields is None:
            fields = _DEFAULT_RETURN_FIELDS
        return self._get_fleets_collection(marker,
                                           limit, sort_key, sort_dir,
                                           project=cdict['project_id'],
                                           fields=fields)

    @expose.expose(Fleet, body=Fleet, status_code=201)
    def post(self, Fleet):
        """Create a new Fleet.

        :param Fleet: a Fleet within the request body.
        """
        context = pecan.request.context
        cdict = context.to_policy_values()
        policy.authorize('iot:fleet:create', cdict, cdict)

        if not Fleet.name:
            raise exception.MissingParameterValue(
                ("Name is not specified."))

        if Fleet.name:
            if not api_utils.is_valid_name(Fleet.name):
                msg = ("Cannot create fleet with invalid name %(name)s")
                raise wsme.exc.ClientSideError(msg % {'name': Fleet.name},
                                               status_code=400)

        new_Fleet = objects.Fleet(pecan.request.context,
                                  **Fleet.as_dict())

        new_Fleet.project = cdict['project_id']
        new_Fleet = pecan.request.rpcapi.create_fleet(
            pecan.request.context,
            new_Fleet)

        return Fleet.convert_with_links(new_Fleet)

    @expose.expose(None, types.uuid_or_name, status_code=204)
    def delete(self, fleet_ident):
        """Delete a fleet.

        :param fleet_ident: UUID or logical name of a fleet.
        """
        context = pecan.request.context
        cdict = context.to_policy_values()
        policy.authorize('iot:fleet:delete', cdict, cdict)

        rpc_fleet = api_utils.get_rpc_fleet(fleet_ident)
        pecan.request.rpcapi.destroy_fleet(pecan.request.context,
                                           rpc_fleet.uuid)

    @expose.expose(Fleet, types.uuid_or_name, body=Fleet, status_code=200)
    def patch(self, fleet_ident, val_Fleet):
        """Update a fleet.

        :param fleet_ident: UUID or logical name of a fleet.
        :param Fleet: values to be changed
        :return updated_fleet: updated_fleet
        """

        rpc_fleet = api_utils.get_rpc_fleet(fleet_ident)
        cdict = pecan.request.context.to_policy_values()
        cdict['project'] = rpc_fleet.project
        policy.authorize('iot:fleet:update', cdict, cdict)

        val_Fleet = val_Fleet.as_dict()
        for key in val_Fleet:
            try:
                rpc_fleet[key] = val_Fleet[key]
            except Exception:
                pass

        updated_fleet = pecan.request.rpcapi.update_fleet(
            pecan.request.context, rpc_fleet)
        return Fleet.convert_with_links(updated_fleet)

    @expose.expose(FleetCollection, types.uuid, int, wtypes.text,
                   wtypes.text, types.listtype, types.boolean, types.boolean)
    def detail(self, marker=None,
               limit=None, sort_key='id', sort_dir='asc',
               fields=None, with_public=False, all_fleets=False):
        """Retrieve a list of fleets.

        :param marker: pagination marker for large data sets.
        :param limit: maximum number of resources to return in a single result.
                      This value cannot be larger than the value of max_limit
                      in the [api] section of the ironic configuration, or only
                      max_limit resources will be returned.
        :param sort_key: column to sort results by. Default: id.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.
        :param with_public: Optional boolean to get also public fleet.
        :param all_fleets: Optional boolean to get all the fleets.
                            Only for the admin
        :param fields: Optional, a list with a specified set of fields
                       of the resource to be returned.
        """

        cdict = pecan.request.context.to_policy_values()
        policy.authorize('iot:fleet:get', cdict, cdict)

        # /detail should only work against collections
        parent = pecan.request.path.split('/')[:-1][-1]
        if parent != "fleets":
            raise exception.HTTPNotFound()

        return self._get_fleets_collection(marker,
                                           limit, sort_key, sort_dir,
                                           with_public=with_public,
                                           all_fleets=all_fleets,
                                           fields=fields)
