"""targetofficeuid

Revision ID: 560a7b8ee1b1
Revises: 39b878094b02
Create Date: 2017-04-04 07:35:14.379446

"""

# revision identifiers, used by Alembic.
revision = '560a7b8ee1b1'
down_revision = '39b878094b02'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('campaign_target_office', schema=None) as batch_op:
        batch_op.add_column(sa.Column('uid', sa.String(length=100), nullable=True))
        batch_op.create_index(batch_op.f('ix_campaign_target_office_uid'), ['uid'], unique=False)

    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('campaign_target_office', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_campaign_target_office_uid'))
        batch_op.drop_column('uid')

    ### end Alembic commands ###