from .user import User
from ..magic_castle.magic_castle import MagicCastle, MagicCastleORM
from ...configuration.cloud import ALL_CLOUD_ID
from ...database import db


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
        results = MagicCastleORM.query.all()
        return [MagicCastle(orm=orm) for orm in results]

    def create_empty_magic_castle(self):
        return MagicCastle()

    def get_magic_castle_by_hostname(self, hostname):
        orm = MagicCastleORM.query.filter_by(hostname=hostname).first()
        return MagicCastle(orm=orm)
