"""Persist day-before capacity checks and notification deduplication."""
from alembic import op
import sqlalchemy as sa

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("capacity_quota_check",
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("project.id"), primary_key=True),
        sa.Column("checked_at", sa.Float(), nullable=False),
        sa.Column("next_check_at", sa.Float(), nullable=False),
        sa.Column("input_signature", sa.String(64), nullable=False),
        sa.Column("notification_signature", sa.String(64)),
        sa.Column("result", sa.JSON(), nullable=False))


def downgrade():
    op.drop_table("capacity_quota_check")
