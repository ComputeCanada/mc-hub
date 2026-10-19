"""Persist planning intent and a renewable worker lease."""
from alembic import op
import sqlalchemy as sa

revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("terraformcloudrun") as batch:
        batch.add_column(sa.Column("intent_hash", sa.String(64)))
        batch.add_column(sa.Column("lease_owner", sa.String(64)))
        batch.add_column(sa.Column("lease_until", sa.DateTime()))


def downgrade():
    with op.batch_alter_table("terraformcloudrun") as batch:
        batch.drop_column("lease_until")
        batch.drop_column("lease_owner")
        batch.drop_column("intent_hash")
