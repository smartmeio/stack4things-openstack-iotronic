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
revision = 'b578199e4e64'
down_revision = 'df35e9cbeaff'

from alembic import op
import iotronic.db.sqlalchemy.models
import sqlalchemy as sa


def upgrade():
    op.create_table('fleets',
                    sa.Column('created_at', sa.DateTime(), nullable=True),
                    sa.Column('updated_at', sa.DateTime(), nullable=True),
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('uuid', sa.String(length=36), nullable=True),
                    sa.Column('name', sa.String(length=36), nullable=True),
                    sa.Column('project', sa.String(length=36), nullable=True),
                    sa.Column('description', sa.String(length=300),
                              nullable=True),
                    sa.Column('extra',
                              iotronic.db.sqlalchemy.models.JSONEncodedDict(),
                              nullable=True),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('uuid', name='uniq_fleets0uuid')
                    )
