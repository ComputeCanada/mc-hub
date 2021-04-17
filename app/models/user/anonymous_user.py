from models.user.user import User
from models.magic_castle.magic_castle import MagicCastle


class AnonymousUser(User):
    """
    User class for users created when the authentication type is set to NONE.
    """

    def __init__(self, database_connection):
        super().__init__(database_connection)

    def get_all_magic_castles(self):
        """
        Retrieve all the Magic Castles retrieved in the database.
        :return: A list of MagicCastle objects
        """
        results = self._database_connection.execute(
            "SELECT hostname FROM magic_castles"
        ).fetchall()
        return [MagicCastle(result[0]) for result in results]

    def create_empty_magic_castle(self):
        return MagicCastle()

    def get_magic_castle_by_hostname(self, hostname):
        return MagicCastle(hostname)
