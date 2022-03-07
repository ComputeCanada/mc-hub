import sqlite3

from os import listdir, path
from os.path import isfile

from .. configuration.env import SCHEMA_MIGRATIONS_DIRECTORY

class SchemaManager:
    """
    SchemaManager is responsible for updating the database schema to the latest version using migration files contained
    in the `migrations` directory.
    """

    def __init__(self, database_connection: sqlite3.Connection):
        self.__database_connection = database_connection

    def update_schema(self):
        current_version = self.__get_current_version()
        latest_version = self.__get_latest_version()

        # Installs all the new migrations
        for i in range(current_version, latest_version):
            with open(
                path.join(SCHEMA_MIGRATIONS_DIRECTORY, f"{i:04}.sql"), "r"
            ) as migration_file:
                self.__database_connection.executescript(migration_file.read())
                self.__database_connection.commit()
                self.__increment_version()

    def __get_current_version(self):
        return self.__database_connection.execute("PRAGMA user_version").fetchone()[0]

    def __increment_version(self):
        new_version = self.__get_current_version() + 1
        self.__database_connection.execute(f"PRAGMA user_version = {new_version}")
        self.__database_connection.commit()

    def __get_latest_version(self):
        return len(
            [
                migration_file
                for migration_file in listdir(SCHEMA_MIGRATIONS_DIRECTORY)
                if isfile(path.join(SCHEMA_MIGRATIONS_DIRECTORY, migration_file))
            ]
        )
