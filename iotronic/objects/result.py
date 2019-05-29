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

# from oslo_utils import strutils
# from oslo_utils import uuidutils

# from iotronic.common import exception
from iotronic.db import api as db_api
from iotronic.objects import base
from iotronic.objects import utils as obj_utils

SUCCESS = "SUCCESS"
ERROR = "ERROR"
WARNING = "WARNING"
RUNNING = "RUNNING"


class Result(base.IotronicObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    dbapi = db_api.get_instance()

    fields = {
        'id': int,
        'board_uuid': obj_utils.str_or_none,
        'request_uuid': obj_utils.str_or_none,
        'result': obj_utils.str_or_none,
        'message': obj_utils.str_or_none,
    }

    @staticmethod
    def _from_db_object(result, db_result):
        """Converts a database entity to a formal object."""
        for field in result.fields:
            result[field] = db_result[field]
        result.obj_reset_changes()
        return result

    @base.remotable_classmethod
    def get(cls, context, board_uuid, request_uuid):
        """Find a result based on name and return a Board object.

        :param board_uuid: the board uuid result.
        :param request_uuid: the request_uuid.
        :returns: a :class:`result` object.
        """
        db_result = cls.dbapi.get_result(board_uuid, request_uuid)
        result = Result._from_db_object(cls(context), db_result)
        return result

    @base.remotable_classmethod
    def get_results_list(cls, context, filters=None):
        """Find a result based on name and return a Board object.

        :param board_uuid: the board uuid result.
        :param request_uuid: the request_uuid.
        :returns: a :class:`result` object.
        """
        db_requests = cls.dbapi.get_result_list(
            filters=filters)
        return [Result._from_db_object(cls(context), obj)
                for obj in db_requests]

    @base.remotable_classmethod
    def list(cls, context, limit=None, marker=None, sort_key=None,
             sort_dir=None, filters=None):
        """Return a list of Result objects.

        :param context: Security context.
        :param limit: maximum number of resources to return in a
                      single result.
        :param marker: pagination marker for large data sets.
        :param sort_key: column to sort results by.
        :param sort_dir: direction to sort. "asc" or "desc".
        :param filters: Filters to apply.
        :returns: a list of :class:`Result` object.

        """

        db_results = cls.dbapi.get_result_list(filters=filters,
                                               limit=limit,
                                               marker=marker,
                                               sort_key=sort_key,
                                               sort_dir=sort_dir)
        return [Result._from_db_object(cls(context), obj)
                for obj in db_results]

    @base.remotable
    def create(self, context=None):
        """Create a Result record in the DB.

        Column-wise updates will be made based on the result of
        self.what_changed(). If target_power_state is provided,
        it will be checked against the in-database copy of the
        result before updates are made.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Result(context)

        """

        values = self.obj_get_changes()
        db_result = self.dbapi.create_result(values)
        self._from_db_object(self, db_result)

    # @base.remotable
    # def destroy(self, context=None):
    #     """Delete the Result from the DB.
    #
    #     :param context: Security context. NOTE: This should only
    #                     be used internally by the indirection_api.
    #                     Unfortunately, RPC requires context as the first
    #                     argument, even though we don't use it.
    #                     A context should be set when instantiating the
    #                     object, e.g.: Result(context)
    #     """
    #     self.dbapi.destroy_result(self.uuid)
    #     self.obj_reset_changes()

    @base.remotable
    def save(self, context=None):
        """Save updates to this Result.

        Column-wise updates will be made based on the result of
        self.what_changed(). If target_power_state is provided,
        it will be checked against the in-database copy of the
        result before updates are made.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Result(context)
        """
        updates = self.obj_get_changes()
        self.dbapi.update_result(self.id, updates)
        self.obj_reset_changes()
