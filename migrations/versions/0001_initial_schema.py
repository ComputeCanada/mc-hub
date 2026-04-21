"""Initial schema

Revision ID: 0001
Revises:
Create Date: 2026-03-31 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "project",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("admin_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.Enum("aws", "azure", "gcp", "openstack", "ovh", name="provider"), nullable=False),
        sa.Column("github_template", sa.String(), nullable=False),
        sa.Column("env", sa.PickleType(), nullable=True),
        sa.Column("tfcloud_project_id", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        if_not_exists=True,
    )
    op.create_table(
        "user",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("scoped_id", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("scoped_id"),
        if_not_exists=True,
    )
    op.create_table(
        "magiccastle",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("hostname", sa.String(256), nullable=False),
        sa.Column("status", sa.Enum(
            "not_found", "build_running", "provisioning_running",
            "provisioning_success", "provisioning_error", "build_error",
            "destroy_running", "destroy_error", "idle",
            name="clusterstatuscode",
        ), nullable=True),
        sa.Column("created", sa.DateTime(), nullable=True),
        sa.Column("expiration_date", sa.String(32), nullable=True),
        sa.Column("config", sa.PickleType(), nullable=True),
        sa.Column("applied_config", sa.PickleType(), nullable=True),
        sa.Column("tfcloud_workspace", sa.String(256), nullable=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("project.id"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("hostname"),
        if_not_exists=True,
    )
    op.create_table(
        "terraformcloudrun",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.String(256), nullable=True),
        sa.Column("plan", sa.PickleType(), nullable=True),
        sa.Column("apply_log_url", sa.String(), nullable=True),
        sa.Column("tf_state", sa.PickleType(), nullable=True),
        sa.Column("magic_castle_id", sa.Integer(), sa.ForeignKey("magiccastle.id"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        if_not_exists=True,
    )
    op.create_table(
        "projects",
        sa.Column("user_id", sa.String(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("project_id", sa.String(), sa.ForeignKey("project.id"), nullable=False),
        sa.PrimaryKeyConstraint("user_id", "project_id"),
        if_not_exists=True,
    )


def downgrade():
    op.drop_table("projects")
    op.drop_table("terraformcloudrun")
    op.drop_table("magiccastle")
    op.drop_table("user")
    op.drop_table("project")
