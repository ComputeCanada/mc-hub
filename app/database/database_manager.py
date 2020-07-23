import sqlite3
from models.constants import DATABASE_PATH


class DatabaseConnection:
    def __init__(self):
        self.__connection = None

    def __enter__(self) -> sqlite3.Connection:
        self.__connection = sqlite3.connect(DATABASE_PATH)
        return self.__connection

    def __exit__(self, type, value, traceback):
        self.__connection.close()


class DatabaseManager:
    @staticmethod
    def connect() -> DatabaseConnection:
        return DatabaseConnection()
