"""Initialize benchmark integrations before the first deployment run."""
from alembic import op
import sqlalchemy as sa

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("benchmark", sa.Column("setup_status", sa.String(16), nullable=False, server_default="pending"))
    op.add_column("benchmark", sa.Column("setup_error", sa.String))
    op.add_column("magiccastle", sa.Column("benchmark_id", sa.String(36)))
    op.execute("""
        UPDATE magiccastle SET benchmark_id = (
            SELECT benchmark_id FROM benchmark_run
            WHERE benchmark_run.id = magiccastle.benchmark_run_id AND reuse_cluster = 1
        )
    """)
    op.create_index("uq_magiccastle_benchmark", "magiccastle", ["benchmark_id"], unique=True)
    op.execute("""
        UPDATE benchmark SET setup_status = 'ready' WHERE id IN (
            SELECT benchmark_id FROM magiccastle WHERE benchmark_id IS NOT NULL
            AND usage_repository IS NOT NULL AND tfcloud_workspace IS NOT NULL AND eyaml_public_key IS NOT NULL
        )
    """)


def downgrade():
    if op.get_bind().execute(sa.text(
        "SELECT id FROM magiccastle WHERE benchmark_id IS NOT NULL AND benchmark_run_id IS NULL LIMIT 1"
    )).first():
        raise RuntimeError("Archive benchmarks that have not run before downgrading, to preserve integration ownership.")
    op.drop_index("uq_magiccastle_benchmark", table_name="magiccastle")
    with op.batch_alter_table("magiccastle") as batch:
        batch.drop_column("benchmark_id")
    with op.batch_alter_table("benchmark") as batch:
        batch.drop_column("setup_error")
        batch.drop_column("setup_status")
