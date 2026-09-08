"""Retain undeployed clusters and track deployment start time."""
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("magiccastle") as batch:
        batch.add_column(sa.Column("undeployed", sa.Boolean(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("deployment_started_at", sa.DateTime(), nullable=True))


def downgrade():
    with op.batch_alter_table("magiccastle") as batch:
        batch.drop_column("deployment_started_at")
        batch.drop_column("undeployed")
