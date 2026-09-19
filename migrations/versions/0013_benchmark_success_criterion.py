"""Selectable benchmark success criteria with immutable historical targets."""
from alembic import op
import sqlalchemy as sa

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade():
    for table in ("benchmark", "benchmark_run"):
        op.add_column(table, sa.Column("success_criterion", sa.String(24), nullable=False, server_default="healthy"))
    op.add_column("benchmark_run", sa.Column("target_reached_at", sa.DateTime))
    op.execute("UPDATE benchmark_run SET target_reached_at = healthy_at")


def downgrade():
    with op.batch_alter_table("benchmark_run") as batch:
        batch.drop_column("target_reached_at")
        batch.drop_column("success_criterion")
    with op.batch_alter_table("benchmark") as batch:
        batch.drop_column("success_criterion")
