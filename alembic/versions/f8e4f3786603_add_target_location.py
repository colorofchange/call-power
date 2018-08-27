"""add target.location

Revision ID: f8e4f3786603
Revises: 7f361698d677
Create Date: 2018-01-10 19:31:52.822512

"""

# revision identifiers, used by Alembic.
revision = 'f8e4f3786603'
down_revision = '7f361698d677'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('campaign_target', schema=None) as batch_op:
        batch_op.add_column(sa.Column('location', sa.String(length=100), nullable=True))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('campaign_target', schema=None) as batch_op:
        batch_op.drop_column('location')
    ### end Alembic commands ###
