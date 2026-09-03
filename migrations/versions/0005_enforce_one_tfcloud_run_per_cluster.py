"""Enforce one Terraform Cloud run per Magic Castle

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-03 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()

    # The ORM relationship has always been scalar, but the database previously
    # allowed several runs to reference the same castle. Keep the most recently
    # inserted run before adding the missing database invariant.
    bind.execute(
        sa.text(
            """
            DELETE FROM terraformcloudrun
            WHERE magic_castle_id IS NOT NULL
              AND id NOT IN (
                  SELECT MAX(id)
                  FROM terraformcloudrun
                  WHERE magic_castle_id IS NOT NULL
                  GROUP BY magic_castle_id
              )
            """
        )
    )

    with op.batch_alter_table("terraformcloudrun") as batch_op:
        batch_op.create_unique_constraint(
            "uq_terraformcloudrun_magic_castle_id",
            ["magic_castle_id"],
        )


def downgrade():
    with op.batch_alter_table("terraformcloudrun") as batch_op:
        batch_op.drop_constraint(
            "uq_terraformcloudrun_magic_castle_id",
            type_="unique",
        )
