from pathlib import Path

import sqlalchemy as sa
from flask_migrate import upgrade

from .mocks.configuration.config_mock import config_auth_none_mock  # noqa: F401


def test_tfcloud_run_migration_deduplicates_existing_rows(tmp_path):
    from mchub import create_app
    from mchub.database import db

    database_path = tmp_path / "migration.db"
    migrations_path = Path(__file__).parents[1] / "migrations"
    app = create_app(db_path=f"sqlite:///{database_path}")

    with app.app_context():
        upgrade(directory=str(migrations_path), revision="0004")
        db.session.execute(
            sa.text(
                "INSERT INTO magiccastle (hostname) VALUES ('duplicate.example.com')"
            )
        )
        magic_castle_id = db.session.execute(
            sa.text(
                "SELECT id FROM magiccastle WHERE hostname = 'duplicate.example.com'"
            )
        ).scalar_one()
        db.session.execute(
            sa.text(
                """
                INSERT INTO terraformcloudrun (run_id, magic_castle_id)
                VALUES ('OLD_RUN', :magic_castle_id),
                       ('CURRENT_RUN', :magic_castle_id)
                """
            ),
            {"magic_castle_id": magic_castle_id},
        )
        db.session.commit()

        upgrade(directory=str(migrations_path), revision="head")

        runs = db.session.execute(
            sa.text(
                """
                SELECT run_id
                FROM terraformcloudrun
                WHERE magic_castle_id = :magic_castle_id
                """
            ),
            {"magic_castle_id": magic_castle_id},
        ).scalars().all()
        assert runs == ["CURRENT_RUN"]

        constraints = sa.inspect(db.engine).get_unique_constraints(
            "terraformcloudrun"
        )
        assert any(
            constraint["column_names"] == ["magic_castle_id"]
            for constraint in constraints
        )
