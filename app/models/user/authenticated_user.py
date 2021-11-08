from models.user.user import User
from exceptions.invalid_usage_exception import ClusterNotFoundException
from models.magic_castle.magic_castle import MagicCastle
from models.configuration import config


class AuthenticatedUser(User):
    """
    User class for users created when the authentication type is set to SAML.

    An authenticated user can be an admin or a regular user. An admin can view
    and edit clusters created by anyone, while a regular user can only view and
    edit his own clusters.
    """

    def __init__(
        self,
        database_connection,
        *,
        edu_person_principal_name,
        given_name,
        surname,
        mail,
        ssh_public_key,
    ):
        super().__init__(database_connection)
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

    def is_admin(self):
        try:
            return self.edu_person_principal_name in config["admins"]
        except KeyError:
            return False

    def get_all_magic_castles(self):
        """
        If the user is admin, it will retrieve all the clusters,
        otherwise, only the clusters owned by the user.

        :return: A list of MagicCastle objects
        """
        query = "SELECT hostname, owner FROM magic_castles"
        args = ()
        if not self.is_admin():
            query = " ".join([query, "WHERE owner = ?"])
            args += (self.edu_person_principal_name,)
        results = self._database_connection.execute(query, args)
        return [MagicCastle(hostname, owner) for hostname, owner in results]

    def create_empty_magic_castle(self):
        return MagicCastle(owner=self.edu_person_principal_name)

    def get_magic_castle_by_hostname(self, hostname):
        query = "SELECT hostname, owner FROM magic_castles WHERE hostname = ?"
        args = (hostname,)
        if not self.is_admin():
            query = " ".join([query, "AND owner = ?"])
            args += (self.edu_person_principal_name,)

        row = self._database_connection.execute(query, args).fetchone()
        if row:
            return MagicCastle(hostname=row[0], owner=row[1])
        else:
            raise ClusterNotFoundException
