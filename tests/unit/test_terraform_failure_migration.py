import importlib
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text


def test_failure_migration_preserves_existing_clusters():
    migration = importlib.import_module('migrations.versions.0018_terraform_failure')
    with create_engine('sqlite://').begin() as connection:
        connection.execute(text('CREATE TABLE magiccastle (id INTEGER PRIMARY KEY, hostname TEXT)'))
        connection.execute(text("INSERT INTO magiccastle VALUES (1, 'existing.example')"))
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
            assert tuple(connection.execute(text('SELECT hostname, terraform_failure FROM magiccastle')).one()) == ('existing.example', None)
            migration.downgrade()
        assert [column['name'] for column in inspect(connection).get_columns('magiccastle')] == ['id', 'hostname']
