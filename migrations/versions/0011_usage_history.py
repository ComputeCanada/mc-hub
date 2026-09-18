"""Retain adoption history and apply-to-healthy measurements."""
import uuid
from alembic import op
import sqlalchemy as sa

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade():
    for table in ("magiccastle", "project"):
        op.add_column(table, sa.Column("usage_id", sa.String(36)))
        conn = op.get_bind()
        for row in conn.execute(sa.text(f"SELECT id FROM {table}")):
            conn.execute(sa.text(f"UPDATE {table} SET usage_id = :uid WHERE id = :id"),
                         {"uid": str(uuid.uuid4()), "id": row.id})
        with op.batch_alter_table(table) as batch:
            batch.alter_column("usage_id", existing_type=sa.String(36), nullable=False)
    op.add_column("magiccastle", sa.Column("usage_legacy", sa.Boolean, nullable=False, server_default="0"))
    op.execute("UPDATE magiccastle SET usage_legacy = 1")
    op.add_column("magiccastle", sa.Column("usage_repository", sa.String))
    op.add_column("terraformcloudrun", sa.Column("commit_sha", sa.String(64)))
    op.create_table("usage_state",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("tracking_started_at", sa.DateTime, nullable=False),
        sa.Column("last_poll_at", sa.DateTime))
    op.execute("INSERT INTO usage_state (id, tracking_started_at) VALUES (1, CURRENT_TIMESTAMP)")
    op.create_table("usage_lifetime",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("cluster_id", sa.String(36), nullable=False),
        sa.Column("active_cluster_id", sa.String(36), unique=True),
        sa.Column("hostname", sa.String(256), nullable=False),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("project_name", sa.String, nullable=False),
        sa.Column("provider", sa.String, nullable=False),
        sa.Column("creator", sa.String), sa.Column("repository", sa.String),
        sa.Column("predates_tracking", sa.Boolean, nullable=False),
        sa.Column("started_at", sa.DateTime), sa.Column("healthy_at", sa.DateTime),
        sa.Column("ended_at", sa.DateTime))
    op.create_index("ix_usage_lifetime_cluster_id", "usage_lifetime", ["cluster_id"])
    op.create_table("usage_apply",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("lifetime_id", sa.String(36), nullable=False),
        sa.Column("run_id", sa.String(256), nullable=False, unique=True),
        sa.Column("commit_sha", sa.String(64)), sa.Column("initiated_by", sa.String),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("requested_at", sa.DateTime, nullable=False),
        sa.Column("applied_at", sa.DateTime), sa.Column("healthy_at", sa.DateTime),
        sa.Column("outcome", sa.String(24), nullable=False))
    op.create_index("ix_usage_apply_lifetime_id", "usage_apply", ["lifetime_id"])


def downgrade():
    for table in ("usage_apply", "usage_lifetime", "usage_state"):
        op.drop_table(table)
    with op.batch_alter_table("terraformcloudrun") as batch:
        batch.drop_column("commit_sha")
    with op.batch_alter_table("magiccastle") as batch:
        batch.drop_column("usage_repository")
        batch.drop_column("usage_legacy")
        batch.drop_column("usage_id")
    with op.batch_alter_table("project") as batch:
        batch.drop_column("usage_id")
