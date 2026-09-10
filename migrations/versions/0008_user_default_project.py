"""Save each user's default cloud project."""
from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("user") as batch:
        batch.add_column(sa.Column("default_project_id", sa.Integer(), nullable=True))
        batch.create_foreign_key(
            "fk_user_default_project", "project", ["default_project_id"], ["id"],
            ondelete="SET NULL",
        )
    # Preserve the editor's previous first-project choice: direct membership first.
    op.execute(sa.text('''
        UPDATE "user" SET default_project_id = COALESCE(
            (SELECT MIN(CAST(project_id AS INTEGER)) FROM projects WHERE user_id = "user".id),
            (SELECT MIN(project_id) FROM project_admins WHERE user_id = "user".id)
        )
    '''))


def downgrade():
    with op.batch_alter_table("user") as batch:
        batch.drop_constraint("fk_user_default_project", type_="foreignkey")
        batch.drop_column("default_project_id")
