from models.magic_castle import MagicCastle
from models.constants import CLUSTERS_PATH
from database.database_manager import DatabaseManager


class MagicCastleManager:
    def __init__(self, database_connection):
        self.__database_connection = database_connection

    def all(self):
        """
        Retrieve all the Magic Castles retrieved in the database.
        :return: A list of MagicCastle objects
        """
        results = self.__database_connection.execute(
            "SELECT hostname FROM magic_castles"
        ).fetchall()
        return [
            MagicCastle(self.__database_connection, result[0]) for result in results
        ]

    def create_empty(self):
        return MagicCastle(self.__database_connection)

    def get_by_hostname(self, hostname):
        return MagicCastle(self.__database_connection, hostname)
