"""Reuse benchmark hostnames and integrations across runs."""
from alembic import op
import sqlalchemy as sa

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade():
    # Older definitions reserve their configured name on their next save/run.
    op.add_column("benchmark", sa.Column("cluster_name", sa.String(63)))
    op.create_index("uq_benchmark_cluster_name", "benchmark", ["cluster_name"], unique=True)
    with op.batch_alter_table("benchmark_run", naming_convention={"uq": "uq_%(table_name)s_%(column_0_name)s"}) as batch:
        batch.drop_constraint("uq_benchmark_run_hostname", type_="unique")
        batch.add_column(sa.Column("reuse_cluster", sa.Boolean, nullable=False, server_default=sa.false()))


def downgrade():
    duplicates = op.get_bind().execute(sa.text(
        "SELECT hostname FROM benchmark_run GROUP BY hostname HAVING COUNT(*) > 1 LIMIT 1"
    )).first()
    if duplicates:
        raise RuntimeError("Cannot downgrade while benchmark runs share hostnames; retain migration 0014 to preserve history.")
    with op.batch_alter_table("benchmark_run") as batch:
        batch.drop_column("reuse_cluster")
        batch.create_unique_constraint("uq_benchmark_run_hostname", ["hostname"])
    op.drop_index("uq_benchmark_cluster_name", table_name="benchmark")
    with op.batch_alter_table("benchmark") as batch:
        batch.drop_column("cluster_name")
