"""Add cluster_token to magiccastle

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-31 09:03:24.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    existing_columns = {col["name"] for col in inspect(bind).get_columns("magiccastle")}
    if "cluster_token" not in existing_columns:
        with op.batch_alter_table("magiccastle") as batch_op:
            batch_op.add_column(sa.Column("cluster_token", sa.String(64), nullable=True))
            batch_op.create_unique_constraint("uq_magiccastle_cluster_token", ["cluster_token"])


def downgrade():
    with op.batch_alter_table("magiccastle") as batch_op:
        batch_op.drop_constraint("uq_magiccastle_cluster_token", type_="unique")
        batch_op.drop_column("cluster_token")
