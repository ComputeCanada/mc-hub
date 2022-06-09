from subprocess import getoutput
from typing import List
from getpass import getuser

from .magic_castle.magic_castle import MagicCastle, MagicCastleORM
from ..database import db
from ..configuration import config
from .cloud.project import Project


projects = db.Table(
    "projects",
    db.Column("user_id", db.String(), db.ForeignKey("user.id"), primary_key=True),
    db.Column("project_id", db.String(), db.ForeignKey("project.id"), primary_key=True),
)


class UserORM(db.Model):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    scoped_id = db.Column(db.String(), unique=True)
    projects = db.relationship("Project", secondary=projects)


class User:
    __slots__ = ["orm", "username", "usertype", "public_keys"]

    def __init__(self, orm, username, usertype, public_keys=[]):
        self.orm = orm
        self.username = username
        self.usertype = usertype
        self.public_keys = public_keys

    @property
    def projects(self):
        return self.orm.projects

    def query_magic_castles(self) -> List[MagicCastle]:
        raise NotImplementedError

    def create_empty_magic_castle(self) -> MagicCastle:
        raise NotImplementedError


class LocalUser(User):
    """
    User class for users created when the authentication type is set to NONE.
    """

    def __init__(self, orm):
        try:
            public_keys = getoutput("ssh-add -L").split("\n")
        except:
            public_keys = []
        username = getuser()
        super().__init__(
            orm=orm, username=username, usertype="local", public_keys=public_keys
        )

    def query_magic_castles(self, **filter_):
        """
        Retrieve all the Magic Castles retrieved in the database.
        :return: A list of MagicCastle objects
        """
        results = MagicCastleORM.query.filter_by(**filter_)
        return [MagicCastle(orm=orm) for orm in results.all()]

    def create_empty_magic_castle(self):
        return MagicCastle()


class SAMLUser(User):
    """
    User class for users created when the authentication type is set to SAML.

    An authenticated user can be an admin or a regular user. An admin can view
    and edit clusters created by anyone, while a regular user can only view and
    edit his own clusters.
    """

    __slots__ = ["scoped_id", "scope", "given_name", "surname", "mail"]

    def __init__(
        self,
        *,
        orm,
        edu_person_principal_name,
        given_name,
        surname,
        mail,
        ssh_public_key,
    ):
        username, scope = edu_person_principal_name.split("@")
        super().__init__(
            orm=orm,
            username=username,
            usertype="saml",
            public_keys=ssh_public_key.split(";"),
        )
        self.scoped_id = edu_person_principal_name
        self.scope = scope
        self.given_name = given_name
        self.surname = surname
        self.mail = mail

    def query_magic_castles(self, **filter_):
        """
        If the user is admin, it will retrieve all the clusters,
        otherwise, only the clusters owned by the user.

        :return: A list of MagicCastle objects
        """
        filter_["owner"] = self.scoped_id
        results = MagicCastleORM.query.filter_by(**filter_)
        return [MagicCastle(orm=orm) for orm in results.all()]

    def create_empty_magic_castle(self):
        return MagicCastle(owner=self.scoped_id)
