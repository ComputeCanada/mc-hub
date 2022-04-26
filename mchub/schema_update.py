import argparse

from . database.cleanup_manager import CleanupManager
from . database.database_manager import DatabaseManager
from . database.schema_manager import SchemaManager


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Updates the database schema with the new schema migrations."
    )
    parser.add_argument('--clean', action="store_true")
    arguments = parser.parse_args()

    # Update the database schema to the latest version
    with DatabaseManager.connect() as database_connection:
        SchemaManager(database_connection).update_schema()
        if arguments.clean:
            CleanupManager(database_connection).clean_status()
