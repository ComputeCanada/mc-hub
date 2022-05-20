from . user import User
from .. magic_castle.magic_castle import MagicCastle
from ... configuration.cloud import ALL_CLOUD_ID
from ... database.database_manager import DatabaseManager

class AnonymousUser(User):
    """
    User class for users created when the authentication type is set to NONE.
    """

    def __init__(self):
        super().__init__()

    @property
    def projects(self):
        return ALL_CLOUD_ID

    def get_all_magic_castles(self):
        """
        Retrieve all the Magic Castles retrieved in the database.
        :return: A list of MagicCastle objects
        """
        with DatabaseManager.connect() as database_connection:
            results = database_connection.execute(
                "SELECT hostname FROM magic_castles"
            ).fetchall()
        return [MagicCastle(result[0]) for result in results]

    def create_empty_magic_castle(self):
        return MagicCastle()

    def get_magic_castle_by_hostname(self, hostname):
        return MagicCastle(hostname)
