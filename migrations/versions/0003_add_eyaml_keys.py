"""Add eyaml_public_key to magiccastle

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-21 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    # Existing clusters will have eyaml_public_key=NULL and won't support eyaml encryption.
    with op.batch_alter_table("magiccastle") as batch_op:
        batch_op.add_column(sa.Column("eyaml_public_key", sa.Text, nullable=True))


def downgrade():
    with op.batch_alter_table("magiccastle") as batch_op:
        batch_op.drop_column("eyaml_public_key")
