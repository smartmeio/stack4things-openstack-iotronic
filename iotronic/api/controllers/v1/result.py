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
from iotronic.api.controllers.v1 import types
from iotronic.api.controllers.v1 import utils as api_utils
from iotronic.api import expose
from iotronic.common import exception
from iotronic.common import policy
from iotronic import objects

_DEFAULT_RETURN_FIELDS = (
    'board_uuid',
    'request_uuid',
    'result',
)


class Result(base.APIBase):
    """API representation of a result.

    """
    board_uuid = types.uuid
    request_uuid = types.uuid
    result = wsme.wsattr(wtypes.text)
    message = wsme.wsattr(wtypes.text)

    links = wsme.wsattr([link.Link], readonly=True)

    def __init__(self, **kwargs):
        self.fields = []
        fields = list(objects.Result.fields)
        for k in fields:
            # Skip fields we do not expose.
            if not hasattr(self, k):
                continue
            self.fields.append(k)
            setattr(self, k, kwargs.get(k, wtypes.Unset))

    @staticmethod
    def _convert_with_links(result, fields=None):
        if fields is not None:
            result.unset_fields_except(fields)
        return result

    @classmethod
    def convert_with_links(cls, rpc_result, fields=None):
        result = Result(**rpc_result.as_dict())

        if fields is not None:
            api_utils.check_for_invalid_fields(fields, result.as_dict())

        return cls._convert_with_links(result,
                                       fields=fields)


class ResultCollection(collection.Collection):
    """API representation of a collection of results."""

    results = [Result]
    """A list containing results objects"""

    def __init__(self, **kwargs):
        self._type = 'results'

    @staticmethod
    def convert_with_links(results, limit, url=None, fields=None, **kwargs):
        collection = ResultCollection()
        collection.results = [Result.convert_with_links(n, fields=fields)
                              for n in results]
        collection.next = collection.get_next(limit, url=url, **kwargs)
        return collection


class ResultsController(rest.RestController):
    """REST controller for Results."""

    invalid_sort_key_list = ['extra', ]

    _custom_actions = {
        'detail': ['GET'],
    }

    def _get_results_collection(self, marker, limit,
                                sort_key, sort_dir,
                                project=None,
                                fields=None):

        limit = api_utils.validate_limit(limit)
        sort_dir = api_utils.validate_sort_dir(sort_dir)

        marker_obj = None
        if marker:
            marker_obj = objects.Result.get_by_uuid(pecan.result.context,
                                                    marker)

        if sort_key in self.invalid_sort_key_list:
            raise exception.InvalidParameterValue(
                ("The sort_key value %(key)s is an invalid field for "
                 "sorting") % {'key': sort_key})

        filters = {}

        if project:
            if pecan.result.context.is_admin:
                filters['project_id'] = project
        results = objects.Result.list(pecan.result.context, limit,
                                      marker_obj,
                                      sort_key=sort_key, sort_dir=sort_dir,
                                      filters=filters)

        parameters = {'sort_key': sort_key, 'sort_dir': sort_dir}

        return ResultCollection.convert_with_links(results, limit,
                                                   fields=fields,
                                                   **parameters)

    @expose.expose(Result, types.uuid_or_name, types.listtype)
    def get_one(self, result_ident, fields=None):
        """Retrieve information about the given result.

        :param result_ident: UUID or logical name of a result.
        :param fields: Optional, a list with a specified set of fields
            of the resource to be returned.
        """

        cdict = pecan.result.context.to_policy_values()
        policy.authorize('iot:result:get_one', cdict, cdict)

        rpc_result = objects.Result.get_by_uuid(pecan.result.context,
                                                result_ident)
        return Result.convert_with_links(rpc_result, fields=fields)

    @expose.expose(ResultCollection, types.uuid, int, wtypes.text,
                   wtypes.text, types.listtype, types.boolean, types.boolean)
    def get_all(self, request_uuid, marker=None,
                limit=None, sort_key='id', sort_dir='asc',
                fields=None):
        """Retrieve a list of results.

        :param marker: pagination marker for large data sets.
        :param limit: maximum number of resources to return in a single result.
                      This value cannot be larger than the value of max_limit
                      in the [api] section of the ironic configuration, or only
                      max_limit resources will be returned.
        :param sort_key: column to sort results by. Default: id.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.
        :param with_public: Optional boolean to get also public pluings.
        :param all_results: Optional boolean to get all the pluings.
                            Only for the admin
        :param fields: Optional, a list with a specified set of fields
                       of the resource to be returned.
        """
        cdict = pecan.result.context.to_policy_values()
        policy.authorize('iot:result:get', cdict, cdict)

        if fields is None:
            fields = _DEFAULT_RETURN_FIELDS
        return self._get_results_collection(marker,
                                            limit, sort_key, sort_dir,
                                            request_uuid=request_uuid,
                                            fields=fields)

    @expose.expose(ResultCollection, types.uuid, int, wtypes.text,
                   wtypes.text, types.listtype, types.boolean, types.boolean)
    def detail(self, marker=None,
               limit=None, sort_key='id', sort_dir='asc',
               fields=None, with_public=False, all_results=False):
        """Retrieve a list of results.

        :param marker: pagination marker for large data sets.
        :param limit: maximum number of resources to return in a single result.
                      This value cannot be larger than the value of max_limit
                      in the [api] section of the ironic configuration, or only
                      max_limit resources will be returned.
        :param sort_key: column to sort results by. Default: id.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.
        :param with_public: Optional boolean to get also public result.
        :param all_results: Optional boolean to get all the results.
                            Only for the admin
        :param fields: Optional, a list with a specified set of fields
                       of the resource to be returned.
        """

        cdict = pecan.result.context.to_policy_values()
        policy.authorize('iot:result:get', cdict, cdict)

        # /detail should only work against collections
        parent = pecan.result.path.split('/')[:-1][-1]
        if parent != "results":
            raise exception.HTTPNotFound()

        return self._get_results_collection(marker,
                                            limit, sort_key, sort_dir,
                                            with_public=with_public,
                                            all_results=all_results,
                                            fields=fields)
