"""Track initial cluster plan creation progress.

Revision ID: 0005
Revises: 0004
"""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("magiccastle") as batch_op:
        batch_op.add_column(sa.Column("creation_step", sa.String(32), nullable=True))


def downgrade():
    with op.batch_alter_table("magiccastle") as batch_op:
        batch_op.drop_column("creation_step")
