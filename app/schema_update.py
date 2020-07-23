import argparse
from database.database_manager import DatabaseManager
from database.schema_manager import SchemaManager


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Updates the database schema with the new schema migrations."
    )
    arguments = parser.parse_args()

    with DatabaseManager.connect() as database_connection:
        SchemaManager(database_connection).update_schema()
