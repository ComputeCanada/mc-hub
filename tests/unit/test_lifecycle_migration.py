import importlib

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text


def test_lifecycle_migration_preserves_existing_clusters():
    migration = importlib.import_module("migrations.versions.0006_cluster_lifecycle")
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE magiccastle (id INTEGER PRIMARY KEY, hostname TEXT)"))
        connection.execute(text("INSERT INTO magiccastle VALUES (1, 'existing.example')"))
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
            row = connection.execute(text("SELECT hostname, undeployed, deployment_started_at FROM magiccastle")).one()
            assert tuple(row) == ("existing.example", 0, None)
            migration.downgrade()
        assert [column["name"] for column in inspect(connection).get_columns("magiccastle")] == ["id", "hostname"]
