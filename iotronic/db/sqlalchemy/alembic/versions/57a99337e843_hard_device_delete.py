"""hard device delete

Revision ID: 57a99337e843
Revises: 76c628d60004
Create Date: 2020-07-07 15:45:20.892424

"""

# revision identifiers, used by Alembic.
revision = '57a99337e843'
down_revision = '76c628d60004'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('enabled_webservices_ibfk_1', 'enabled_webservices', type_='foreignkey')
    op.create_foreign_key(None, 'enabled_webservices', 'boards', ['board_uuid'], ['uuid'], ondelete='CASCADE')
    op.drop_constraint('exposed_services_ibfk_1', 'exposed_services', type_='foreignkey')
    op.create_foreign_key(None, 'exposed_services', 'boards', ['board_uuid'], ['uuid'], ondelete='CASCADE')
    op.drop_constraint('injection_plugins_ibfk_1', 'injection_plugins', type_='foreignkey')
    op.create_foreign_key(None, 'injection_plugins', 'boards', ['board_uuid'], ['uuid'], ondelete='CASCADE')
    op.drop_constraint('locations_ibfk_1', 'locations', type_='foreignkey')
    op.create_foreign_key(None, 'locations', 'boards', ['board_id'], ['id'], ondelete='CASCADE')
    op.drop_constraint('ports_on_boards_ibfk_1', 'ports_on_boards', type_='foreignkey')
    op.create_foreign_key(None, 'ports_on_boards', 'boards', ['board_uuid'], ['uuid'], ondelete='CASCADE')
    op.alter_column('requests', 'action',
               existing_type=mysql.VARCHAR(length=20),
               nullable=True)
    op.alter_column('requests', 'destination_uuid',
               existing_type=mysql.VARCHAR(length=36),
               nullable=True)
    op.alter_column('requests', 'pending_requests',
               existing_type=mysql.INTEGER(display_width=11),
               nullable=True)
    op.alter_column('requests', 'status',
               existing_type=mysql.VARCHAR(length=10),
               nullable=True)
    op.alter_column('requests', 'type',
               existing_type=mysql.INTEGER(display_width=11),
               nullable=True)
    op.alter_column('requests', 'uuid',
               existing_type=mysql.VARCHAR(length=36),
               nullable=True)
    op.alter_column('results', 'board_uuid',
               existing_type=mysql.VARCHAR(length=36),
               nullable=True)
    op.alter_column('results', 'request_uuid',
               existing_type=mysql.VARCHAR(length=36),
               nullable=True)
    op.alter_column('results', 'result',
               existing_type=mysql.VARCHAR(length=10),
               nullable=True)
    op.drop_constraint('results_ibfk_1', 'results', type_='foreignkey')
    op.drop_constraint('results_ibfk_2', 'results', type_='foreignkey')
    op.drop_constraint('sessions_ibfk_1', 'sessions', type_='foreignkey')
    op.create_foreign_key(None, 'sessions', 'boards', ['board_id'], ['id'], ondelete='CASCADE')
    op.create_unique_constraint('uniq_webservices0uuid', 'webservices', ['uuid'])
    op.drop_index('uniq_enabled_webservices0uuid', table_name='webservices')
    op.drop_constraint('webservices_ibfk_1', 'webservices', type_='foreignkey')
    op.create_foreign_key(None, 'webservices', 'boards', ['board_uuid'], ['uuid'], ondelete='CASCADE')
    # ### end Alembic commands ###
