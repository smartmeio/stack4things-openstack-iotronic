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

# revision identifiers, used by Alembic.
revision = '76c628d60004'
down_revision = 'b98819997377'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table('requests',
                    sa.Column('created_at', sa.DateTime(), nullable=True),
                    sa.Column('updated_at', sa.DateTime(), nullable=True),
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('uuid', sa.String(length=36), nullable=False),
                    sa.Column('destination_uuid', sa.String(length=36),
                              nullable=False),
                    sa.Column('main_request_uuid', sa.String(length=36),
                              nullable=True),
                    sa.Column('pending_requests', sa.Integer(), default=0,
                              nullable=False),
                    sa.Column('project', sa.String(length=36), nullable=True),
                    sa.Column('status', sa.String(length=10), nullable=False),
                    sa.Column('type', sa.Integer(), nullable=False),
                    sa.Column('action', sa.String(length=20), nullable=False),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('uuid', name='uniq_requests0uuid'),
                    sa.ForeignKeyConstraint(['main_request_uuid'],
                                            ['requests.uuid'], )
                    )

    op.create_table('results',
                    sa.Column('created_at', sa.DateTime(), nullable=True),
                    sa.Column('updated_at', sa.DateTime(), nullable=True),
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('result', sa.String(length=10), nullable=False),
                    sa.Column('message', sa.TEXT(), nullable=True),
                    sa.Column('board_uuid', sa.String(length=36),
                              nullable=False),
                    sa.Column('request_uuid', sa.String(length=36),
                              nullable=False),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('board_uuid', 'request_uuid',
                                        name='uniq_request_on_board'),
                    sa.ForeignKeyConstraint(['board_uuid'],
                                            ['boards.uuid'], ),
                    sa.ForeignKeyConstraint(['request_uuid'],
                                            ['requests.uuid'], )
                    )
