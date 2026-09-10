import importlib

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

migration = importlib.import_module("migrations.versions.0009_unique_project_name")


def test_unique_name_migration_preserves_projects_and_can_be_reversed():
    with create_engine("sqlite://").begin() as connection:
        connection.execute(text("CREATE TABLE project (id INTEGER PRIMARY KEY, name TEXT NOT NULL)"))
        connection.execute(text("INSERT INTO project VALUES (1, 'cloud')"))
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
            assert connection.execute(text("SELECT id, name FROM project")).all() == [(1, "cloud")]
            with pytest.raises(IntegrityError):
                connection.execute(text("INSERT INTO project VALUES (2, 'cloud')"))
            migration.downgrade()
            connection.execute(text("INSERT INTO project VALUES (2, 'cloud')"))
        assert connection.execute(text("SELECT COUNT(*) FROM project")).scalar() == 2


def test_migration_refuses_existing_duplicates_without_changing_them():
    with create_engine("sqlite://").begin() as connection:
        connection.execute(text("CREATE TABLE project (id INTEGER PRIMARY KEY, name TEXT NOT NULL)"))
        connection.execute(text("INSERT INTO project VALUES (1, 'cloud'), (2, 'cloud')"))
        with Operations.context(MigrationContext.configure(connection)):
            with pytest.raises(RuntimeError, match="Duplicate project names exist"):
                migration.upgrade()
        assert connection.execute(text("SELECT id, name FROM project")).all() == [(1, "cloud"), (2, "cloud")]
        assert inspect(connection).get_indexes("project") == []
