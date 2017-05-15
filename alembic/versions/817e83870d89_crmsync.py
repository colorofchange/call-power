"""CRMSync

Revision ID: 817e83870d89
Revises: 0c500511ff19
Create Date: 2017-04-22 14:04:23.304971

"""

# revision identifiers, used by Alembic.
revision = '817e83870d89'
down_revision = '0c500511ff19'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('sync_campaign',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_time', sa.DateTime(), nullable=True),
    sa.Column('last_sync_time', sa.DateTime(), nullable=True),
    sa.Column('campaign_id', sa.Integer(), nullable=True),
    sa.Column('crm_id', sa.String(length=40), nullable=True),
    sa.ForeignKeyConstraint(['campaign_id'], ['campaign_campaign.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('sync_call',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_time', sa.DateTime(), nullable=True),
    sa.Column('call_id', sa.Integer(), nullable=True),
    sa.Column('synced', sa.Boolean(), nullable=True),
    sa.ForeignKeyConstraint(['call_id'], ['calls.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('sync_call')
    op.drop_table('sync_campaign')
    ### end Alembic commands ###
