"""call session direction

Revision ID: 58fd841f12d7
Revises: 2e693a9ad462
Create Date: 2017-06-23 12:12:00.578637

"""

# revision identifiers, used by Alembic.
revision = '58fd841f12d7'
down_revision = '2e693a9ad462'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    with op.batch_alter_table('calls_session', schema=None) as batch_op:
        batch_op.add_column(sa.Column('direction', sa.String(length=25), nullable=True, server_default='outbound'))


def downgrade():
    with op.batch_alter_table('calls_session', schema=None) as batch_op:
        batch_op.drop_column('direction')
