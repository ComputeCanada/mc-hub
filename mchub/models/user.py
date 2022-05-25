from subprocess import getoutput
from typing import List

from .magic_castle.magic_castle import MagicCastle, MagicCastleORM
from ..configuration import config
from ..configuration.cloud import DEFAULT_CLOUD, ALL_CLOUD_ID


class User:
    def __init__(self, username=None, full_name=None, public_keys=[]):
        self.username = username
        self.full_name = full_name
        self.public_keys = public_keys

    @property
    def projects(self):
        return []

    def query_magic_castles(self) -> List[MagicCastle]:
        raise NotImplementedError

    def create_empty_magic_castle(self) -> MagicCastle:
        raise NotImplementedError


class LocalUser(User):
    """
    User class for users created when the authentication type is set to NONE.
    """

    def __init__(self):
        try:
            public_keys = getoutput("ssh-add -L").split("\n")
        except:
            public_keys = []
        super().__init__(public_keys=public_keys)

    @property
    def projects(self):
        return ALL_CLOUD_ID

    def query_magic_castles(self, **filter_):
        """
        Retrieve all the Magic Castles retrieved in the database.
        :return: A list of MagicCastle objects
        """
        results = MagicCastleORM.query.filter_by(**filter_)
        return [MagicCastle(orm=orm) for orm in results.all()]

    def create_empty_magic_castle(self):
        return MagicCastle()


class AuthenticatedUser(User):
    """
    User class for users created when the authentication type is set to SAML.

    An authenticated user can be an admin or a regular user. An admin can view
    and edit clusters created by anyone, while a regular user can only view and
    edit his own clusters.
    """

    def __init__(
        self,
        *,
        edu_person_principal_name,
        given_name,
        surname,
        mail,
        ssh_public_key,
    ):
        username, scope = self.scoped_id.split("@")
        super().__init__(
            username=username,
            full_name=f"{given_name} {surname}",
            public_keys=ssh_public_key.split(";"),
        )
        self.scoped_id = edu_person_principal_name
        self.scope = scope
        self.given_name = given_name
        self.surname = surname
        self.mail = mail

    @property
    def projects(self):
        # with DatabaseManager.connect() as database_connection:
        #     results = database_connection.execute(
        #         "SELECT projects FROM users WHERE username = ?",
        #         (self.edu_person_principal_name,),
        #     ).fetchone()
        # if results:
        #     return json.loads(results[0])
        return [DEFAULT_CLOUD]

    def is_admin(self):
        return self.scoped_id in config.get("admins", [])

    def query_magic_castles(self, **filter_):
        """
        If the user is admin, it will retrieve all the clusters,
        otherwise, only the clusters owned by the user.

        :return: A list of MagicCastle objects
        """
        if not self.is_admin():
            filter_["owner"] = self.scoped_id
        results = MagicCastleORM.query.filter_by(**filter_)
        return [MagicCastle(orm=orm) for orm in results.all()]

    def create_empty_magic_castle(self):
        return MagicCastle(owner=self.scoped_id)
