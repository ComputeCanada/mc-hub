"""Project capacity plans."""
from alembic import op
import sqlalchemy as sa

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("capacity_plan",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("project.id"), nullable=False),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("starts_at", sa.Float(), nullable=False),
        sa.Column("ends_at", sa.Float(), nullable=False),
        sa.Column("definition", sa.JSON(), nullable=False),
        sa.Column("demand", sa.JSON(), nullable=False),
        sa.Column("auto_create", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("message", sa.String(255)),
        sa.Column("cluster_usage_id", sa.String(36)))
    op.create_index("ix_capacity_plan_project_id", "capacity_plan", ["project_id"])


def downgrade():
    op.drop_table("capacity_plan")
