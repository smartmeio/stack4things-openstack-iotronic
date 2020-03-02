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

from iotronic.db import api as db_api
from iotronic.objects import base
from iotronic.objects import utils as obj_utils


class ExposedService(base.IotronicObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    dbapi = db_api.get_instance()

    fields = {
        'id': int,
        'board_uuid': obj_utils.str_or_none,
        'service_uuid': obj_utils.str_or_none,
        'public_port': int
    }

    @base.remotable_classmethod
    def get_all_ports(cls, context):
        ls = cls.list(context)
        ports = []
        for x in ls:
            ports.append(x.public_port)
        return ports

    @staticmethod
    def _from_db_object(exposed_service, db_exposed_service):
        """Converts a database entity to a formal object."""
        for field in exposed_service.fields:
            exposed_service[field] = db_exposed_service[field]
        exposed_service.obj_reset_changes()
        return exposed_service

    @base.remotable_classmethod
    def get_by_id(cls, context, exposed_service_id):
        """Find a exposed_service based on its integer id and return a Board object.

        :param exposed_service_id: the id of a exposed_service.
        :returns: a :class:`exposed_service` object.
        """
        db_exp_service = cls.dbapi.get_exposed_service_by_id(
            exposed_service_id)
        exp_service = ExposedService._from_db_object(cls(context),
                                                     db_exp_service)
        return exp_service

    @base.remotable_classmethod
    def get_by_board_uuid(cls, context, board_uuid):
        """Return a list of ExposedService objects.

        :param context: Security context.
        :param limit: maximum number of resources to return in a single result.
        :param marker: pagination marker for large data sets.
        :param sort_key: column to sort results by.
        :param sort_dir: direction to sort. "asc" or "desc".
        :param filters: Filters to apply.
        :returns: a list of :class:`ExposedService` object.

        """
        db_exps = cls.dbapi.get_exposed_services_by_board_uuid(board_uuid)
        return [ExposedService._from_db_object(cls(context), obj)
                for obj in db_exps]

    @base.remotable_classmethod
    def get_by_service_uuid(cls, context, service_uuid):
        """Find a exposed_service based on uuid and return a Board object.

        :param service_uuid: the uuid of a exposed_service.
        :returns: a :class:`exposed_service` object.
        """
        db_exp_service = cls.dbapi.get_exposed_service_by_service_uuid(
            service_uuid)
        exp_service = ExposedService._from_db_object(cls(context),
                                                     db_exp_service)
        return exp_service

    @base.remotable_classmethod
    def get(cls, context, board_uuid, service_uuid):
        """Find a exposed_service based on uuid and return a Service object.

        :param board_uuid: the uuid of a exposed_service.
        :returns: a :class:`exposed_service` object.
        """
        db_exp_service = cls.dbapi.get_exposed_service_by_uuids(board_uuid,
                                                                service_uuid)
        exp_service = ExposedService._from_db_object(cls(context),
                                                     db_exp_service)
        return exp_service

    @base.remotable_classmethod
    def list(cls, context, board_uuid=None):
        """Return a list of ExposedService objects.

        :param context: Security context.
        :param limit: maximum number of resources to return in a single result.
        :param marker: pagination marker for large data sets.
        :param sort_key: column to sort results by.
        :param sort_dir: direction to sort. "asc" or "desc".
        :param filters: Filters to apply.
        :returns: a list of :class:`ExposedService` object.

        """
        db_exps = cls.dbapi.get_exposed_service_list(board_uuid)
        return [ExposedService._from_db_object(cls(context), obj)
                for obj in db_exps]

    @base.remotable
    def create(self, context=None):
        """Create a ExposedService record in the DB.

        Column-wise updates will be made based on the result of
        self.what_changed(). If target_power_state is provided,
        it will be checked against the in-database copy of the
        exposed_service before updates are made.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: ExposedService(context)

        """
        values = self.obj_get_changes()
        db_exposed_service = self.dbapi.create_exposed_service(values)
        self._from_db_object(self, db_exposed_service)

    @base.remotable
    def destroy(self, context=None):
        """Delete the ExposedService from the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: ExposedService(context)
        """
        self.dbapi.destroy_exposed_service(self.id)
        self.obj_reset_changes()

    @base.remotable
    def save(self, context=None):
        """Save updates to this ExposedService.

        Column-wise updates will be made based on the result of
        self.what_changed(). If target_power_state is provided,
        it will be checked against the in-database copy of the
        exposed_service before updates are made.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: ExposedService(context)
        """
        updates = self.obj_get_changes()
        self.dbapi.update_exposed_service(self.id, updates)
        self.obj_reset_changes()
