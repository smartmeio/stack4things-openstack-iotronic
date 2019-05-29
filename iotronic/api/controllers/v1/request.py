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


import pecan
from pecan import rest
import wsme
from wsme import types as wtypes

from iotronic.api.controllers import base
from iotronic.api.controllers import link
from iotronic.api.controllers.v1 import collection
from iotronic.api.controllers.v1.result import ResultCollection
from iotronic.api.controllers.v1 import types
from iotronic.api.controllers.v1 import utils as api_utils
from iotronic.api import expose
from iotronic.common import exception
from iotronic.common import policy
from iotronic import objects

_DEFAULT_RETURN_FIELDS = (
    'uuid',
    'destination_uuid',
    'main_request_uuid',
    'pending_requests',
    'status',
    'type',
    'action'
)

_DEFAULT_RESULT_RETURN_FIELDS = (
    'board_uuid',
    'request_uuid',
    'result',
    'message'
)


class Request(base.APIBase):
    """API representation of a request.

    """

    uuid = types.uuid
    destination_uuid = types.uuid
    main_request_uuid = types.uuid
    pending_requests = wsme.types.IntegerType()
    status = wsme.wsattr(wtypes.text)
    project = types.uuid
    type = wsme.types.IntegerType()
    action = wsme.wsattr(wtypes.text)

    links = wsme.wsattr([link.Link], readonly=True)

    def __init__(self, **kwargs):
        self.fields = []
        fields = list(objects.Request.fields)
        for k in fields:
            # Skip fields we do not expose.
            if not hasattr(self, k):
                continue
            self.fields.append(k)
            setattr(self, k, kwargs.get(k, wtypes.Unset))

    @staticmethod
    def _convert_with_links(request, url, fields=None):
        request_uuid = request.uuid
        if fields is not None:
            request.unset_fields_except(fields)

        request.links = [link.Link.make_link('self', url, 'requests',
                                             request_uuid),
                         link.Link.make_link('bookmark', url, 'requests',
                                             request_uuid, bookmark=True)
                         ]
        return request

    @classmethod
    def convert_with_links(cls, rpc_request, fields=None):
        request = Request(**rpc_request.as_dict())

        if fields is not None:
            api_utils.check_for_invalid_fields(fields, request.as_dict())

        return cls._convert_with_links(request, pecan.request.public_url,
                                       fields=fields)


class RequestCollection(collection.Collection):
    """API representation of a collection of requests."""

    requests = [Request]
    """A list containing requests objects"""

    def __init__(self, **kwargs):
        self._type = 'requests'

    @staticmethod
    def convert_with_links(requests, limit, url=None, fields=None, **kwargs):
        collection = RequestCollection()
        collection.requests = [Request.convert_with_links(n, fields=fields)
                               for n in requests]
        collection.next = collection.get_next(limit, url=url, **kwargs)
        return collection


class ResultsRequestController(rest.RestController):
    def __init__(self, request_ident):
        self.request_ident = request_ident

    @expose.expose(ResultCollection, types.uuid, int, wtypes.text,
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
        policy.authorize('iot:result:get', cdict, cdict)

        if fields is None:
            fields = _DEFAULT_RESULT_RETURN_FIELDS

        filters = {}
        filters['request_uuid'] = self.request_ident

        results = objects.Result.list(pecan.request.context, limit, marker,
                                      sort_key=sort_key, sort_dir=sort_dir,
                                      filters=filters)

        parameters = {'sort_key': sort_key, 'sort_dir': sort_dir}

        return ResultCollection.convert_with_links(results, limit,
                                                   fields=fields,
                                                   **parameters)


class RequestsController(rest.RestController):
    """REST controller for Requests."""

    _subcontroller_map = {
        'results': ResultsRequestController,
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
            return subcontroller(request_ident=ident), remainder[1:]

    def _get_requests_collection(self, marker, limit,
                                 sort_key, sort_dir,
                                 project=None,
                                 fields=None):

        limit = api_utils.validate_limit(limit)
        sort_dir = api_utils.validate_sort_dir(sort_dir)

        marker_obj = None
        if marker:
            marker_obj = objects.Request.get_by_uuid(pecan.request.context,
                                                     marker)

        if sort_key in self.invalid_sort_key_list:
            raise exception.InvalidParameterValue(
                ("The sort_key value %(key)s is an invalid field for "
                 "sorting") % {'key': sort_key})

        filters = {}

        if project:
            if pecan.request.context.is_admin:
                filters['project_id'] = project
        requests = objects.Request.list(pecan.request.context, limit,
                                        marker_obj,
                                        sort_key=sort_key, sort_dir=sort_dir,
                                        filters=filters)

        parameters = {'sort_key': sort_key, 'sort_dir': sort_dir}

        return RequestCollection.convert_with_links(requests, limit,
                                                    fields=fields,
                                                    **parameters)

    @expose.expose(Request, types.uuid_or_name, types.listtype)
    def get_one(self, request_ident, fields=None):
        """Retrieve information about the given request.

        :param request_ident: UUID or logical name of a request.
        :param fields: Optional, a list with a specified set of fields
            of the resource to be returned.
        """

        cdict = pecan.request.context.to_policy_values()
        policy.authorize('iot:request:get_one', cdict, cdict)

        rpc_request = objects.Request.get_by_uuid(pecan.request.context,
                                                  request_ident)
        return Request.convert_with_links(rpc_request, fields=fields)

    @expose.expose(RequestCollection, types.uuid, int, wtypes.text,
                   wtypes.text, types.listtype, types.boolean, types.boolean)
    def get_all(self, marker=None,
                limit=None, sort_key='id', sort_dir='asc',
                fields=None):
        """Retrieve a list of requests.

        :param marker: pagination marker for large data sets.
        :param limit: maximum number of resources to return in a single result.
                      This value cannot be larger than the value of max_limit
                      in the [api] section of the ironic configuration, or only
                      max_limit resources will be returned.
        :param sort_key: column to sort results by. Default: id.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.
        :param with_public: Optional boolean to get also public pluings.
        :param all_requests: Optional boolean to get all the pluings.
                            Only for the admin
        :param fields: Optional, a list with a specified set of fields
                       of the resource to be returned.
        """
        cdict = pecan.request.context.to_policy_values()
        policy.authorize('iot:request:get', cdict, cdict)

        if fields is None:
            fields = _DEFAULT_RETURN_FIELDS
        return self._get_requests_collection(marker,
                                             limit, sort_key, sort_dir,
                                             project=cdict['project_id'],
                                             fields=fields)

    @expose.expose(RequestCollection, types.uuid, int, wtypes.text,
                   wtypes.text, types.listtype, types.boolean, types.boolean)
    def detail(self, marker=None,
               limit=None, sort_key='id', sort_dir='asc',
               fields=None, with_public=False, all_requests=False):
        """Retrieve a list of requests.

        :param marker: pagination marker for large data sets.
        :param limit: maximum number of resources to return in a single result.
                      This value cannot be larger than the value of max_limit
                      in the [api] section of the ironic configuration, or only
                      max_limit resources will be returned.
        :param sort_key: column to sort results by. Default: id.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.
        :param with_public: Optional boolean to get also public request.
        :param all_requests: Optional boolean to get all the requests.
                            Only for the admin
        :param fields: Optional, a list with a specified set of fields
                       of the resource to be returned.
        """

        cdict = pecan.request.context.to_policy_values()
        policy.authorize('iot:request:get', cdict, cdict)

        # /detail should only work against collections
        parent = pecan.request.path.split('/')[:-1][-1]
        if parent != "requests":
            raise exception.HTTPNotFound()

        return self._get_requests_collection(marker,
                                             limit, sort_key, sort_dir,
                                             with_public=with_public,
                                             all_requests=all_requests,
                                             fields=fields)
