import importlib

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

migration = importlib.import_module("migrations.versions.0010_tfcloud_project_name")


def test_migration_preserves_existing_terraform_names_and_scopes_uniqueness():
    with create_engine("sqlite://").begin() as connection:
        connection.execute(text("CREATE TABLE project (id INTEGER PRIMARY KEY, name TEXT NOT NULL)"))
        connection.execute(text("CREATE UNIQUE INDEX uq_project_name ON project(name)"))
        connection.execute(text("INSERT INTO project VALUES (1, 'legacy')"))
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
            assert connection.execute(text("SELECT tfcloud_project_name FROM project")).scalar() == "legacy"
            connection.execute(text("INSERT INTO project VALUES (2, 'legacy', 'alice-legacy')"))
            with pytest.raises(IntegrityError):
                connection.execute(text("INSERT INTO project VALUES (3, 'different', 'alice-legacy')"))
            with pytest.raises(RuntimeError, match="Duplicate display names"):
                migration.downgrade()
            assert connection.execute(text("SELECT COUNT(*) FROM project")).scalar() == 2
            connection.execute(text("DELETE FROM project WHERE id = 2"))
            migration.downgrade()
            assert connection.execute(text("SELECT * FROM project")).all() == [(1, "legacy")]
            with pytest.raises(IntegrityError):
                connection.execute(text("INSERT INTO project VALUES (2, 'legacy')"))
