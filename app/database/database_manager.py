import sqlite3
from os import path
from models.constants import DATABASE_PATH, DATABASE_FILENAME

DATABASE_FILE_PATH = path.join(DATABASE_PATH, DATABASE_FILENAME)


class DatabaseConnection:
    def __init__(self):
        self.__connection = None

    def __enter__(self) -> sqlite3.Connection:
        try:
            self.__connection = sqlite3.connect(DATABASE_FILE_PATH)
        except sqlite3.OperationalError as op_e:
            sqlite3.OperationalError('Could not perform queries on the source database: '
                                     '{}'.format(op_e))
        return self.__connection

    def __exit__(self, type, value, traceback):
        self.__connection.close()


class DatabaseManager:
    @staticmethod
    def connect() -> DatabaseConnection:
        return DatabaseConnection()
