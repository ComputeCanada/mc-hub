"""Durable notification outbox and provider notification baseline."""
from alembic import op
import sqlalchemy as sa

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("service_status_snapshot", sa.Column("notification_snapshot", sa.JSON()))
    op.create_table("notification_event",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("resource_id", sa.String(255), nullable=False),
        sa.Column("created_at", sa.Float(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False))
    op.create_table("notification_delivery",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_id", sa.String(36), sa.ForeignKey("notification_event.id"), nullable=False),
        sa.Column("destination_id", sa.String(100), nullable=False),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("next_attempt_at", sa.Float(), nullable=False),
        sa.Column("delivered_at", sa.Float()),
        sa.Column("last_error", sa.String(255)),
        sa.UniqueConstraint("event_id", "destination_id", name="uq_notification_destination"))
    op.create_index("ix_notification_due", "notification_delivery", ["state", "next_attempt_at"])


def downgrade():
    op.drop_table("notification_delivery")
    op.drop_table("notification_event")
    with op.batch_alter_table("service_status_snapshot") as batch:
        batch.drop_column("notification_snapshot")
