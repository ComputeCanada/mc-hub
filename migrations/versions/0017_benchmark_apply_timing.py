"""Record Terraform's actual apply start for build benchmark measurements."""
from alembic import op
import sqlalchemy as sa

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade():
    # Preserve historical observations without pretending they measure execution.
    op.add_column("benchmark_run", sa.Column("apply_started_at", sa.DateTime))


def downgrade():
    with op.batch_alter_table("benchmark_run") as batch:
        batch.drop_column("apply_started_at")
