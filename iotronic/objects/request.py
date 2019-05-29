# coding=utf-8
#
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

from oslo_utils import strutils
from oslo_utils import uuidutils

from iotronic.common import exception
from iotronic.db import api as db_api
from iotronic.objects import base
from iotronic.objects import utils as obj_utils

BOARD = 0
FLOAT = 1

COMPLETED = "COMPLETED"
PENDING = "PENDING"


class Request(base.IotronicObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    dbapi = db_api.get_instance()

    fields = {
        'id': int,
        'uuid': obj_utils.str_or_none,
        'destination_uuid': obj_utils.str_or_none,
        'main_request_uuid': obj_utils.str_or_none,
        'pending_requests': int,
        'status': obj_utils.str_or_none,
        'project': obj_utils.str_or_none,
        'type': int,
        'action': obj_utils.str_or_none,
    }

    @staticmethod
    def _from_db_object(request, db_request):
        """Converts a database entity to a formal object."""
        for field in request.fields:
            request[field] = db_request[field]
        request.obj_reset_changes()
        return request

    @base.remotable_classmethod
    def get(cls, context, request_id):
        """Find a request based on its id or uuid and return a Board object.

        :param request_id: the id *or* uuid of a request.
        :returns: a :class:`Board` object.
        """
        if strutils.is_int_like(request_id):
            return cls.get_by_id(context, request_id)
        elif uuidutils.is_uuid_like(request_id):
            return cls.get_by_uuid(context, request_id)
        else:
            raise exception.InvalidIdentity(identity=request_id)

    @base.remotable_classmethod
    def get_by_id(cls, context, request_id):
        """Find a request based on its integer id and return a Board object.

        :param request_id: the id of a request.
        :returns: a :class:`Board` object.
        """
        db_request = cls.dbapi.get_request_by_id(request_id)
        request = Request._from_db_object(cls(context), db_request)
        return request

    @base.remotable_classmethod
    def get_by_uuid(cls, context, uuid):
        """Find a request based on uuid and return a Board object.

        :param uuid: the uuid of a request.
        :returns: a :class:`Board` object.
        """
        db_request = cls.dbapi.get_request_by_uuid(uuid)
        request = Request._from_db_object(cls(context), db_request)
        return request

    # @base.remotable_classmethod
    # def get_results(cls, context, filters=None):
    #     """Find a request based on uuid and return a Board object.
    #
    #     :param uuid: the uuid of a request.
    #     :returns: a :class:`Board` object.
    #     """
    #     return Result.get_results_list(context,
    #                                    filters)

    # @base.remotable_classmethod
    # def get_results_request(cls,context,request_uuid):
    #     db_requests = cls.dbapi.get_results(request_uuid)
    #     return [Result._from_db_object(cls(context), obj)
    #                  for obj in db_requests]

    # @base.remotable_classmethod
    # def get_by_name(cls, context, name):
    #     """Find a request based on name and return a Board object.
    #
    #     :param name: the logical name of a request.
    #     :returns: a :class:`Board` object.
    #     """
    #     db_request = cls.dbapi.get_request_by_name(name)
    #     request = Request._from_db_object(cls(context), db_request)
    #     return request

    @base.remotable_classmethod
    def list(cls, context, limit=None, marker=None, sort_key=None,
             sort_dir=None, filters=None):
        """Return a list of Request objects.

        :param context: Security context.
        :param limit: maximum number of resources to return in a
                      single result.
        :param marker: pagination marker for large data sets.
        :param sort_key: column to sort results by.
        :param sort_dir: direction to sort. "asc" or "desc".
        :param filters: Filters to apply.
        :returns: a list of :class:`Request` object.

        """
        db_requests = cls.dbapi.get_request_list(filters=filters,
                                                 limit=limit,
                                                 marker=marker,
                                                 sort_key=sort_key,
                                                 sort_dir=sort_dir)

        return [Request._from_db_object(cls(context), obj)
                for obj in db_requests]

    @base.remotable
    def create(self, context=None):
        """Create a Request record in the DB.

        Column-wise updates will be made based on the result of
        self.what_changed(). If target_power_state is provided,
        it will be checked against the in-database copy of the
        request before updates are made.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Request(context)

        """

        values = self.obj_get_changes()
        db_request = self.dbapi.create_request(values)
        self._from_db_object(self, db_request)

    # @base.remotable
    # def destroy(self, context=None):
    #     """Delete the Request from the DB.
    #
    #     :param context: Security context. NOTE: This should only
    #                     be used internally by the indirection_api.
    #                     Unfortunately, RPC requires context as the first
    #                     argument, even though we don't use it.
    #                     A context should be set when instantiating the
    #                     object, e.g.: Request(context)
    #     """
    #     self.dbapi.destroy_request(self.uuid)
    #     self.obj_reset_changes()

    @base.remotable
    def save(self, context=None):
        """Save updates to this Request.

        Column-wise updates will be made based on the result of
        self.what_changed(). If target_power_state is provided,
        it will be checked against the in-database copy of the
        request before updates are made.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Request(context)
        """
        updates = self.obj_get_changes()
        self.dbapi.update_request(self.uuid, updates)
        self.obj_reset_changes()
