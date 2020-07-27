from models.user.user import User
from exceptions.cluster_not_found_exception import ClusterNotFoundException
from models.magic_castle.magic_castle import MagicCastle


class AuthenticatedUser(User):
    def __init__(
        self,
        database_connection,
        *,
        edu_person_principal_name,
        given_name,
        surname,
        mail,
    ):
        super().__init__(database_connection)
        self.edu_person_principal_name = edu_person_principal_name
        self.given_name = given_name
        self.surname = surname
        self.mail = mail

    @property
    def full_name(self):
        return f"{self.given_name} {self.surname}"

    @property
    def username(self):
        return self.edu_person_principal_name.split("@")[0]

    def get_all_magic_castles(self):
        """
        Retrieve all the Magic Castles retrieved in the database.
        :return: A list of MagicCastle objects
        """
        results = self._database_connection.execute(
            "SELECT hostname FROM magic_castles WHERE owner = ?",
            (self.edu_person_principal_name,),
        ).fetchall()
        return [
            MagicCastle(
                self._database_connection,
                result[0],
                owner=self.edu_person_principal_name,
            )
            for result in results
        ]

    def create_empty_magic_castle(self):
        return MagicCastle(
            self._database_connection, owner=self.edu_person_principal_name
        )

    def get_magic_castle_by_hostname(self, hostname):
        if self._database_connection.execute(
            "SELECT * FROM magic_castles WHERE owner = ? AND hostname = ?",
            (self.edu_person_principal_name, hostname),
        ).fetchone():
            return MagicCastle(
                self._database_connection,
                hostname,
                owner=self.edu_person_principal_name,
            )
        else:
            raise ClusterNotFoundException
