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
from iotronic.api.controllers.v1 import collection
from iotronic.api.controllers.v1 import location as loc
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

_DEFAULT_RETURN_FIELDS = ('name', 'code', 'status', 'uuid', 'session', 'type')


class Node(base.APIBase):
    """API representation of a node.

    """
    uuid = types.uuid
    code = wsme.wsattr(wtypes.text)
    status = wsme.wsattr(wtypes.text)
    name = wsme.wsattr(wtypes.text)
    type = wsme.wsattr(wtypes.text)
    owner = types.uuid
    session = wsme.wsattr(wtypes.text)
    project = types.uuid
    mobile = types.boolean
    location = wsme.wsattr([loc.Location])
    extra = types.jsontype

    def __init__(self, **kwargs):
        self.fields = []
        fields = list(objects.Node.fields)
        for k in fields:
            # Skip fields we do not expose.
            if not hasattr(self, k):
                continue
            self.fields.append(k)
            setattr(self, k, kwargs.get(k, wtypes.Unset))

    @staticmethod
    def _convert_with_links(node, url, fields=None):
        node_uuid = node.uuid
        if fields is not None:
            node.unset_fields_except(fields)

        node.links = [link.Link.make_link('self', url, 'nodes',
                                          node_uuid),
                      link.Link.make_link('bookmark', url, 'nodes',
                                          node_uuid, bookmark=True)
                      ]
        return node

    @classmethod
    def convert_with_links(cls, rpc_node, fields=None):
        node = Node(**rpc_node.as_dict())

        try:
            session = objects.SessionWP.get_session_by_node_uuid(
                pecan.request.context, node.uuid)
            node.session = session.session_id
        except Exception:
            node.session = None

        try:
            list_loc = objects.Location.list_by_node_uuid(
                pecan.request.context, node.uuid)
            node.location = loc.Location.convert_with_list(list_loc)
        except Exception:
            node.location = []

        # to enable as soon as a better session and location management
        # is implemented
        # if fields is not None:
        #    api_utils.check_for_invalid_fields(fields, node_dict)

        return cls._convert_with_links(node,
                                       pecan.request.public_url,
                                       fields=fields)


class NodeCollection(collection.Collection):
    """API representation of a collection of nodes."""

    nodes = [Node]
    """A list containing nodes objects"""

    def __init__(self, **kwargs):
        self._type = 'nodes'

    @staticmethod
    def convert_with_links(nodes, limit, url=None, fields=None, **kwargs):
        collection = NodeCollection()
        collection.nodes = [Node.convert_with_links(n, fields=fields)
                            for n in nodes]
        collection.next = collection.get_next(limit, url=url, **kwargs)
        return collection


class NodesController(rest.RestController):
    """REST controller for Nodes."""

    invalid_sort_key_list = ['extra', 'location']

    _custom_actions = {
        'detail': ['GET'],
    }

    def _get_nodes_collection(self, marker, limit,
                              sort_key, sort_dir,
                              project=None,
                              resource_url=None, fields=None):

        limit = api_utils.validate_limit(limit)
        sort_dir = api_utils.validate_sort_dir(sort_dir)

        marker_obj = None
        if marker:
            marker_obj = objects.Node.get_by_uuid(pecan.request.context,
                                                  marker)

        if sort_key in self.invalid_sort_key_list:
            raise exception.InvalidParameterValue(
                ("The sort_key value %(key)s is an invalid field for "
                 "sorting") % {'key': sort_key})

        filters = {}

        # bounding the request to a project
        if project:
            if pecan.request.context.is_admin:
                filters['project_id'] = project
            else:
                msg = ("Project parameter can be used only "
                       "by the administrator.")
                raise wsme.exc.ClientSideError(msg,
                                               status_code=400)
        else:
            filters['project_id'] = pecan.request.context.project_id

        nodes = objects.Node.list(pecan.request.context, limit, marker_obj,
                                  sort_key=sort_key, sort_dir=sort_dir,
                                  filters=filters)

        parameters = {'sort_key': sort_key, 'sort_dir': sort_dir}

        return NodeCollection.convert_with_links(nodes, limit,
                                                 url=resource_url,
                                                 fields=fields,
                                                 **parameters)

    @expose.expose(Node, types.uuid_or_name, types.listtype)
    def get_one(self, node_ident, fields=None):
        """Retrieve information about the given node.

        :param node_ident: UUID or logical name of a node.
        :param fields: Optional, a list with a specified set of fields
            of the resource to be returned.
        """

        cdict = pecan.request.context.to_policy_values()
        policy.authorize('iot:node:get', cdict, cdict)

        rpc_node = api_utils.get_rpc_node(node_ident)

        return Node.convert_with_links(rpc_node, fields=fields)

    @expose.expose(NodeCollection, types.uuid, int, wtypes.text,
                   wtypes.text, types.listtype, wtypes.text)
    def get_all(self, marker=None,
                limit=None, sort_key='id', sort_dir='asc',
                fields=None):
        """Retrieve a list of nodes.

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
        policy.authorize('iot:node:get', cdict, cdict)

        if fields is None:
            fields = _DEFAULT_RETURN_FIELDS
        return self._get_nodes_collection(marker,
                                          limit, sort_key, sort_dir,
                                          fields=fields)

    @expose.expose(Node, body=Node, status_code=201)
    def post(self, Node):
        """Create a new Node.

        :param Node: a Node within the request body.
        """
        context = pecan.request.context
        cdict = context.to_policy_values()
        policy.authorize('iot:node:create', cdict, cdict)

        if not Node.name:
            raise exception.MissingParameterValue(
                ("Name is not specified."))
        if not Node.code:
            raise exception.MissingParameterValue(
                ("Code is not specified."))
        if not Node.location:
            raise exception.MissingParameterValue(
                ("Location is not specified."))

        if Node.name:
            if not api_utils.is_valid_node_name(Node.name):
                msg = ("Cannot create node with invalid name %(name)s")
                raise wsme.exc.ClientSideError(msg % {'name': Node.name},
                                               status_code=400)

        new_Node = objects.Node(pecan.request.context,
                                **Node.as_dict())

        new_Node.owner = pecan.request.context.user_id
        new_Node.project = pecan.request.context.project_id

        new_Location = objects.Location(pecan.request.context,
                                        **Node.location[0].as_dict())

        new_Node = pecan.request.rpcapi.create_node(pecan.request.context,
                                                    new_Node, new_Location)

        return Node.convert_with_links(new_Node)

    @expose.expose(None, types.uuid_or_name, status_code=204)
    def delete(self, node_ident):
        """Delete a node.

        :param node_ident: UUID or logical name of a node.
        """
        context = pecan.request.context
        cdict = context.to_policy_values()
        policy.authorize('iot:node:delete', cdict, cdict)

        rpc_node = api_utils.get_rpc_node(node_ident)
        pecan.request.rpcapi.destroy_node(pecan.request.context,
                                          rpc_node.uuid)

    @expose.expose(Node, types.uuid_or_name, body=Node, status_code=200)
    def patch(self, node_ident, val_Node):
        """Update a node.

        :param node_ident: UUID or logical name of a node.
        :param Node: values to be changed
        :return updated_node: updated_node
        """

        context = pecan.request.context
        cdict = context.to_policy_values()
        policy.authorize('iot:node:update', cdict, cdict)

        node = api_utils.get_rpc_node(node_ident)
        val_Node = val_Node.as_dict()
        for key in val_Node:
            try:
                node[key] = val_Node[key]
            except Exception:
                pass

        updated_node = pecan.request.rpcapi.update_node(pecan.request.context,
                                                        node)
        return Node.convert_with_links(updated_node)

    @expose.expose(NodeCollection, types.uuid, int, wtypes.text,
                   wtypes.text, types.listtype, wtypes.text)
    def detail(self, marker=None,
               limit=None, sort_key='id', sort_dir='asc',
               fields=None, project=None):
        """Retrieve a list of nodes.

        :param marker: pagination marker for large data sets.
        :param limit: maximum number of resources to return in a single result.
                      This value cannot be larger than the value of max_limit
                      in the [api] section of the ironic configuration, or only
                      max_limit resources will be returned.
        :param sort_key: column to sort results by. Default: id.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.
        :param project: Optional string value to get only nodes of the project.
        :param fields: Optional, a list with a specified set of fields
                       of the resource to be returned.
        """

        cdict = pecan.request.context.to_policy_values()
        policy.authorize('iot:node:get', cdict, cdict)

        # /detail should only work against collections
        parent = pecan.request.path.split('/')[:-1][-1]
        if parent != "nodes":
            raise exception.HTTPNotFound()

        return self._get_nodes_collection(marker,
                                          limit, sort_key, sort_dir,
                                          project=project,
                                          fields=fields)
