"""add campaign org type

Revision ID: 7bb5d8acd21d
Revises: 560a7b8ee1b1
Create Date: 2017-05-15 13:10:35.955973

"""

# revision identifiers, used by Alembic.
revision = '7bb5d8acd21d'
down_revision = '560a7b8ee1b1'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('campaign_campaign', sa.Column('org_type', sa.String(100)))

def downgrade():
    op.drop_column('campaign_campaign', 'org_type')
