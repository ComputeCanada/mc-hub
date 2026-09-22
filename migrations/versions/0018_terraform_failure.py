"""Persist the latest Terraform failure across deployment attempts."""
from alembic import op
import sqlalchemy as sa

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("magiccastle", sa.Column("terraform_failure", sa.JSON()))


def downgrade():
    with op.batch_alter_table("magiccastle") as batch:
        batch.drop_column("terraform_failure")
