"""add campaign tags

Revision ID: 8373fb5a625e
Revises: 7bb5d8acd21d
Create Date: 2017-05-16 15:42:19.059985

"""

# revision identifiers, used by Alembic.
revision = '8373fb5a625e'
down_revision = '7bb5d8acd21d'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column('campaign_campaign', sa.Column('tags', sa.Text))


def downgrade():
    op.drop_column('campaign_campaign', 'tags')
