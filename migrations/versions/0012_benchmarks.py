"""Scheduled project benchmarks and isolated usage history."""
from alembic import op
import sqlalchemy as sa

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("magiccastle", sa.Column("benchmark_run_id", sa.String(36)))
    op.create_index("uq_magiccastle_benchmark_run", "magiccastle", ["benchmark_run_id"], unique=True)
    op.add_column("usage_lifetime", sa.Column("benchmark_run_id", sa.String(36)))
    op.create_table("benchmark",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.Integer, nullable=False),
        sa.Column("project_key", sa.String(36), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("configuration", sa.JSON, nullable=False),
        sa.Column("frequency", sa.String(16), nullable=False),
        sa.Column("timeout_minutes", sa.Integer, nullable=False),
        sa.Column("enabled", sa.Boolean, nullable=False),
        sa.Column("archived", sa.Boolean, nullable=False),
        sa.Column("next_run_at", sa.DateTime, nullable=False),
        sa.Column("created_by", sa.String, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("revision", sa.Integer, nullable=False))
    op.create_index("ix_benchmark_project_id", "benchmark", ["project_id"])
    op.create_table("benchmark_run",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("benchmark_id", sa.String(36), nullable=False),
        sa.Column("active_benchmark_id", sa.String(36), unique=True),
        sa.Column("configuration", sa.JSON, nullable=False),
        sa.Column("revision", sa.Integer, nullable=False),
        sa.Column("timeout_minutes", sa.Integer, nullable=False),
        sa.Column("hostname", sa.String(256), nullable=False, unique=True),
        sa.Column("requested_by", sa.String),
        sa.Column("requested_at", sa.DateTime, nullable=False),
        sa.Column("started_at", sa.DateTime), sa.Column("applied_at", sa.DateTime),
        sa.Column("healthy_at", sa.DateTime), sa.Column("finished_at", sa.DateTime),
        sa.Column("cleanup_at", sa.DateTime), sa.Column("next_attempt_at", sa.DateTime, nullable=False),
        sa.Column("phase", sa.String(24), nullable=False), sa.Column("outcome", sa.String(24)),
        sa.Column("error", sa.String), sa.Column("cleanup_error", sa.String),
        sa.Column("terraform_run_id", sa.String(256)), sa.Column("commit_sha", sa.String(64)),
        sa.Column("repository", sa.String))
    op.create_index("ix_benchmark_run_benchmark_id", "benchmark_run", ["benchmark_id"])


def downgrade():
    op.drop_table("benchmark_run")
    op.drop_table("benchmark")
    with op.batch_alter_table("usage_lifetime") as batch:
        batch.drop_column("benchmark_run_id")
    op.drop_index("uq_magiccastle_benchmark_run", table_name="magiccastle")
    with op.batch_alter_table("magiccastle") as batch:
        batch.drop_column("benchmark_run_id")
