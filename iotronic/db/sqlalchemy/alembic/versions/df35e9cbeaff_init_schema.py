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

revision = 'df35e9cbeaff'
down_revision = None

from alembic import op
import iotronic.db.sqlalchemy.models
import sqlalchemy as sa


def upgrade():
    op.create_table('boards',
                    sa.Column('created_at', sa.DateTime(), nullable=True),
                    sa.Column('updated_at', sa.DateTime(), nullable=True),
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('uuid', sa.String(length=36), nullable=True),
                    sa.Column('code', sa.String(length=25), nullable=True),
                    sa.Column('status', sa.String(length=15), nullable=True),
                    sa.Column('name', sa.String(length=255), nullable=True),
                    sa.Column('type', sa.String(length=255), nullable=True),
                    sa.Column('agent', sa.String(length=255), nullable=True),
                    sa.Column('owner', sa.String(length=36), nullable=True),
                    sa.Column('project', sa.String(length=36), nullable=True),
                    sa.Column('mobile', sa.Boolean(), nullable=True),
                    sa.Column('config',
                              iotronic.db.sqlalchemy.models.JSONEncodedDict(),
                              nullable=True),
                    sa.Column('extra',
                              iotronic.db.sqlalchemy.models.JSONEncodedDict(),
                              nullable=True),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('code', name='uniq_boards0code'),
                    sa.UniqueConstraint('uuid', name='uniq_boards0uuid')
                    )
    op.create_table('conductors',
                    sa.Column('created_at', sa.DateTime(), nullable=True),
                    sa.Column('updated_at', sa.DateTime(), nullable=True),
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('hostname', sa.String(length=255),
                              nullable=False),
                    sa.Column('online', sa.Boolean(), nullable=True),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('hostname',
                                        name='uniq_conductors0hostname')
                    )
    op.create_table('plugins',
                    sa.Column('created_at', sa.DateTime(), nullable=True),
                    sa.Column('updated_at', sa.DateTime(), nullable=True),
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('uuid', sa.String(length=36), nullable=True),
                    sa.Column('name', sa.String(length=36), nullable=True),
                    sa.Column('owner', sa.String(length=36), nullable=True),
                    sa.Column('public', sa.Boolean(), nullable=True),
                    sa.Column('code', sa.TEXT(), nullable=True),
                    sa.Column('callable', sa.Boolean(), nullable=True),
                    sa.Column('parameters',
                              iotronic.db.sqlalchemy.models.JSONEncodedDict(),
                              nullable=True),
                    sa.Column('extra',
                              iotronic.db.sqlalchemy.models.JSONEncodedDict(),
                              nullable=True),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('uuid', name='uniq_plugins0uuid')
                    )
    op.create_table('services',
                    sa.Column('created_at', sa.DateTime(), nullable=True),
                    sa.Column('updated_at', sa.DateTime(), nullable=True),
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('uuid', sa.String(length=36), nullable=True),
                    sa.Column('name', sa.String(length=36), nullable=True),
                    sa.Column('project', sa.String(length=36), nullable=True),
                    sa.Column('port', sa.Integer(), nullable=True),
                    sa.Column('protocol', sa.String(length=3), nullable=True),
                    sa.Column('extra',
                              iotronic.db.sqlalchemy.models.JSONEncodedDict(),
                              nullable=True),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('uuid', name='uniq_services0uuid')
                    )
    op.create_table('wampagents',
                    sa.Column('created_at', sa.DateTime(), nullable=True),
                    sa.Column('updated_at', sa.DateTime(), nullable=True),
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('hostname', sa.String(length=255),
                              nullable=False),
                    sa.Column('wsurl', sa.String(length=255), nullable=False),
                    sa.Column('online', sa.Boolean(), nullable=True),
                    sa.Column('ragent', sa.Boolean(), nullable=True),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('hostname',
                                        name='uniq_wampagentss0hostname')
                    )
    op.create_table('exposed_services',
                    sa.Column('created_at', sa.DateTime(), nullable=True),
                    sa.Column('updated_at', sa.DateTime(), nullable=True),
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('board_uuid', sa.String(length=36),
                              nullable=True),
                    sa.Column('service_uuid', sa.String(length=36),
                              nullable=True),
                    sa.Column('public_port', sa.Integer(), nullable=True),
                    sa.ForeignKeyConstraint(['board_uuid'], ['boards.uuid'], ),
                    sa.ForeignKeyConstraint(['service_uuid'],
                                            ['services.uuid'], ),
                    sa.PrimaryKeyConstraint('id')
                    )
    op.create_table('injection_plugins',
                    sa.Column('created_at', sa.DateTime(), nullable=True),
                    sa.Column('updated_at', sa.DateTime(), nullable=True),
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('board_uuid', sa.String(length=36),
                              nullable=True),
                    sa.Column('plugin_uuid', sa.String(length=36),
                              nullable=True),
                    sa.Column('onboot', sa.Boolean(), nullable=True),
                    sa.Column('status', sa.String(length=15), nullable=True),
                    sa.ForeignKeyConstraint(['board_uuid'], ['boards.uuid'], ),
                    sa.ForeignKeyConstraint(['plugin_uuid'],
                                            ['plugins.uuid'], ),
                    sa.PrimaryKeyConstraint('id')
                    )
    op.create_table('locations',
                    sa.Column('created_at', sa.DateTime(), nullable=True),
                    sa.Column('updated_at', sa.DateTime(), nullable=True),
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('longitude', sa.String(length=18),
                              nullable=True),
                    sa.Column('latitude', sa.String(length=18), nullable=True),
                    sa.Column('altitude', sa.String(length=18), nullable=True),
                    sa.Column('board_id', sa.Integer(), nullable=True),
                    sa.ForeignKeyConstraint(['board_id'], ['boards.id'], ),
                    sa.PrimaryKeyConstraint('id')
                    )
    op.create_table('ports_on_boards',
                    sa.Column('created_at', sa.DateTime(), nullable=True),
                    sa.Column('updated_at', sa.DateTime(), nullable=True),
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('board_uuid', sa.String(length=40),
                              nullable=True),
                    sa.Column('uuid', sa.String(length=40), nullable=True),
                    sa.Column('VIF_name', sa.String(length=30), nullable=True),
                    sa.Column('MAC_add', sa.String(length=32), nullable=True),
                    sa.Column('ip', sa.String(length=36), nullable=True),
                    sa.Column('network', sa.String(length=36), nullable=True),
                    sa.ForeignKeyConstraint(['board_uuid'], ['boards.uuid'], ),
                    sa.PrimaryKeyConstraint('id')
                    )
    op.create_table('sessions',
                    sa.Column('created_at', sa.DateTime(), nullable=True),
                    sa.Column('updated_at', sa.DateTime(), nullable=True),
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('valid', sa.Boolean(), nullable=True),
                    sa.Column('session_id', sa.String(length=20),
                              nullable=True),
                    sa.Column('board_uuid', sa.String(length=36),
                              nullable=True),
                    sa.Column('board_id', sa.Integer(), nullable=True),
                    sa.ForeignKeyConstraint(['board_id'], ['boards.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint(
                        'session_id', 'board_uuid',
                        name='uniq_board_session_id0session_id')
                    )


def downgrade():
    pass
