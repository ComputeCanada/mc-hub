"""Project-managed notification destinations."""
from alembic import op
import sqlalchemy as sa

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("project_notification_destination",
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("project.id"), primary_key=True),
        sa.Column("delivery_id", sa.String(100), nullable=False, unique=True),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("token", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False))
    # Previously queued capacity warnings must not broadcast project data globally.
    op.execute("UPDATE notification_delivery SET state = 'cancelled' WHERE state = 'pending' "
               "AND event_id IN (SELECT id FROM notification_event WHERE event_type = 'capacity.quota_insufficient')")


def downgrade():
    op.drop_table("project_notification_destination")
