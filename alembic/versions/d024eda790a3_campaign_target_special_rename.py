"""campaign_target_special_rename

Revision ID: d024eda790a3
Revises: 817e83870d89
Create Date: 2018-02-12 16:01:25.519837

"""

# revision identifiers, used by Alembic.
revision = 'd024eda790a3'
down_revision = '817e83870d89'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


campaigns_helper = sa.Table(
        'campaign_campaign',
        sa.MetaData(),
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('include_special', sa.String(length=100)),
    )

def upgrade():
    connection = op.get_bind()

    # rename include_special constants from first/last to before/after
    connection.execute(
        campaigns_helper.update().where(
            campaigns_helper.c.include_special == 'first'
        ).values(
            include_special='before'
        )
    )
    connection.execute(
            campaigns_helper.update().where(
                campaigns_helper.c.include_special == 'last'
            ).values(
                include_special='after'
            )
        )


def downgrade():
    connection = op.get_bind()
    
    # reverse
    connection.execute(
        campaigns_helper.update().where(
            campaigns_helper.c.include_special == 'before'
        ).values(
            include_special='first'
        )
    )
    connection.execute(
            campaigns_helper.update().where(
                campaigns_helper.c.include_special == 'after'
            ).values(
                include_special='last'
            )
        )
