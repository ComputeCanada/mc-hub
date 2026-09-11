"""Track Terraform project names separately from display names."""
from alembic import op
import sqlalchemy as sa

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("project", sa.Column("tfcloud_project_name", sa.String(), nullable=True))
    op.execute(sa.text("UPDATE project SET tfcloud_project_name = name"))
    with op.batch_alter_table("project") as batch:
        batch.alter_column("tfcloud_project_name", existing_type=sa.String(), nullable=False)
    op.create_index("uq_tfcloud_project_name", "project", ["tfcloud_project_name"], unique=True)
    op.drop_index("uq_project_name", table_name="project")


def downgrade():
    duplicate = op.get_bind().execute(sa.text(
        "SELECT name FROM project GROUP BY name HAVING COUNT(*) > 1 LIMIT 1"
    )).first()
    if duplicate is not None:
        raise RuntimeError("Duplicate display names exist. Resolve them before downgrading migration 0010.")
    op.create_index("uq_project_name", "project", ["name"], unique=True)
    op.drop_index("uq_tfcloud_project_name", table_name="project")
    with op.batch_alter_table("project") as batch:
        batch.drop_column("tfcloud_project_name")
