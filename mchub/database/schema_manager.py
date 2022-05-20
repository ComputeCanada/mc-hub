from os import listdir, path
from os.path import isfile

from . database_manager import DatabaseManager

SCHEMA_MIGRATIONS_DIRECTORY = path.join(path.dirname(__file__), 'migrations')

class SchemaManager:
    """
    SchemaManager is responsible for updating the database schema to the latest version using migration files contained
    in the `migrations` directory.
    """
    @classmethod
    def update_schema(cls):
        with DatabaseManager.connect() as db_connection:
            current_version = db_connection.execute("PRAGMA user_version").fetchone()[0]
            latest_version = sum(
                isfile(path.join(SCHEMA_MIGRATIONS_DIRECTORY, migration_file))
                for migration_file in listdir(SCHEMA_MIGRATIONS_DIRECTORY)
            )

            # Installs all the new migrations
            for i in range(current_version, latest_version):
                with open(
                    path.join(SCHEMA_MIGRATIONS_DIRECTORY, f"{i:04}.sql"), "r"
                ) as migration_file:
                    db_connection.executescript(migration_file.read())
                    db_connection.commit()

                    new_version = db_connection.execute("PRAGMA user_version").fetchone()[0] + 1
                    db_connection.execute(f"PRAGMA user_version = {new_version}")
                    db_connection.commit()
