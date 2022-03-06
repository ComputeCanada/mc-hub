import sqlite3
from os import path
from .. configuration.env import DATABASE_PATH
from .. configuration import DATABASE_FILENAME

DATABASE_FILE_PATH = path.join(DATABASE_PATH, DATABASE_FILENAME)


class DatabaseConnection:
    def __init__(self):
        self.__connection = None

    def __enter__(self) -> sqlite3.Connection:
        try:
            self.__connection = sqlite3.connect(
                DATABASE_FILE_PATH,
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
            )
        except sqlite3.OperationalError as op_e:
            raise sqlite3.OperationalError(
                "Could not perform queries on the source database: "
                "{}".format(DATABASE_FILE_PATH)
            )
        return self.__connection

    def __exit__(self, type, value, traceback):
        self.__connection.close()


class DatabaseManager:
    @staticmethod
    def connect() -> DatabaseConnection:
        return DatabaseConnection()
