"""Retain the Git configuration used by repeated benchmark deployments."""
from alembic import op
import sqlalchemy as sa

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade():
    # Older definitions render once on their next run. Historical run SHAs stay
    # unchanged; no equivalence between different commits is inferred.
    op.add_column("magiccastle", sa.Column("benchmark_configuration", sa.JSON))
    op.add_column("magiccastle", sa.Column("benchmark_commit_sha", sa.String(64)))


def downgrade():
    with op.batch_alter_table("magiccastle") as batch:
        batch.drop_column("benchmark_commit_sha")
        batch.drop_column("benchmark_configuration")
