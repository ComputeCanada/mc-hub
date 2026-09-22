"""Cache public provider status across API workers."""
from alembic import op
import sqlalchemy as sa

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("service_status_snapshot",
        sa.Column("provider", sa.String(100), primary_key=True),
        sa.Column("last_success_at", sa.Float()),
        sa.Column("last_attempt_at", sa.Float()),
        sa.Column("last_attempt_ok", sa.Boolean()),
        sa.Column("snapshot", sa.JSON()))


def downgrade():
    op.drop_table("service_status_snapshot")
