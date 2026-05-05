"""Add project_admins table and cluster created_by_user_id; migrate from admin_id

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-28 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    # Create the project_admins join table
    op.create_table(
        "project_admins",
        sa.Column("user_id", sa.Integer, sa.ForeignKey("user.id"), primary_key=True),
        sa.Column("project_id", sa.Integer, sa.ForeignKey("project.id"), primary_key=True),
    )

    # Migrate existing admin_id values into project_admins
    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id, admin_id FROM project WHERE admin_id IS NOT NULL")).fetchall()
    for project_id, admin_id in rows:
        bind.execute(
            sa.text("INSERT OR IGNORE INTO project_admins (user_id, project_id) VALUES (:uid, :pid)"),
            {"uid": admin_id, "pid": project_id},
        )

    # Add created_by_user_id to magiccastle
    with op.batch_alter_table("magiccastle") as batch_op:
        batch_op.add_column(sa.Column("created_by_user_id", sa.Integer, nullable=True))
        batch_op.create_foreign_key("fk_magiccastle_created_by_user_id", "user", ["created_by_user_id"], ["id"])

    # Drop the now-replaced admin_id column from project
    with op.batch_alter_table("project") as batch_op:
        batch_op.drop_column("admin_id")


def downgrade():
    with op.batch_alter_table("project") as batch_op:
        batch_op.add_column(sa.Column("admin_id", sa.Integer, nullable=True))

    with op.batch_alter_table("magiccastle") as batch_op:
        batch_op.drop_column("created_by_user_id")

    op.drop_table("project_admins")
