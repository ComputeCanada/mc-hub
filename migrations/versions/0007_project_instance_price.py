"""Optional AWS per-instance hourly price ceiling."""
from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("project") as batch:
        batch.add_column(sa.Column("max_instance_hourly_price", sa.Numeric(18, 10), nullable=True))


def downgrade():
    with op.batch_alter_table("project") as batch:
        batch.drop_column("max_instance_hourly_price")
