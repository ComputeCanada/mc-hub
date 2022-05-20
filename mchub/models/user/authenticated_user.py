import json

from . user import User
from .. magic_castle.magic_castle import MagicCastle
from ... configuration import config
from ... configuration.cloud import DEFAULT_CLOUD
from ... database.database_manager import DatabaseManager

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
        super().__init__()
        self.edu_person_principal_name = edu_person_principal_name
        self.given_name = given_name
        self.surname = surname
        self.mail = mail
        self.ssh_public_key = ssh_public_key

    @property
    def full_name(self):
        return f"{self.given_name} {self.surname}"

    @property
    def username(self):
        return self.edu_person_principal_name.split("@")[0]

    @property
    def public_keys(self):
        return self.ssh_public_key.split(";")

    @property
    def projects(self):
        with DatabaseManager.connect() as database_connection:
            results = database_connection.execute(
                "SELECT projects FROM users WHERE username = ?",
                (self.edu_person_principal_name,),
            ).fetchone()
        if results:
            return json.loads(results[0])
        return [DEFAULT_CLOUD]

    def is_admin(self):
        return self.edu_person_principal_name in config.get("admins", [])

    def get_all_magic_castles(self):
        """
        If the user is admin, it will retrieve all the clusters,
        otherwise, only the clusters owned by the user.

        :return: A list of MagicCastle objects
        """
        query = "SELECT hostname FROM magic_castles"
        args = ()
        if not self.is_admin():
            query = " ".join([query, "WHERE owner = ?"])
            args += (self.edu_person_principal_name,)
        with DatabaseManager.connect() as database_connection:
            results = database_connection.execute(query, args).fetchall()
        return [MagicCastle(hostname) for hostname, in results]

    def create_empty_magic_castle(self):
        return MagicCastle(owner=self.edu_person_principal_name)

    def get_magic_castle_by_hostname(self, hostname):
        if not self.is_admin():
            owner = self.edu_person_principal_name
        else:
            owner = None
        return MagicCastle(hostname=hostname, owner=owner)
