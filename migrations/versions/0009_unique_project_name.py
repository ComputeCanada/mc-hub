"""Require unique project names across all users and cloud providers."""
from alembic import op
import sqlalchemy as sa

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade():
    duplicate = op.get_bind().execute(sa.text(
        "SELECT name FROM project GROUP BY name HAVING COUNT(*) > 1 LIMIT 1"
    )).first()
    if duplicate is not None:
        raise RuntimeError("Duplicate project names exist. Resolve them before upgrading to migration 0009.")
    op.create_index("uq_project_name", "project", ["name"], unique=True)


def downgrade():
    op.drop_index("uq_project_name", table_name="project")
