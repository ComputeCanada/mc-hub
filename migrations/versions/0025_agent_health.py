"""Persist shared agent health and notification transitions."""
from alembic import op
import sqlalchemy as sa

revision = "0025"
down_revision = "0024"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("agent_health_snapshot",
        sa.Column("organization", sa.String(255), primary_key=True),
        sa.Column("pool_name", sa.String(255), primary_key=True),
        sa.Column("checked_at", sa.Float(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("notified_status", sa.String(32)))


def downgrade():
    op.drop_table("agent_health_snapshot")
