from subprocess import getoutput
from getpass import getuser

from .magic_castle.magic_castle import MagicCastle, MagicCastleORM
from ..database import db
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
    projects = db.relationship(
        "Project",
        secondary=projects,
        lazy="subquery",
        backref=db.backref("members", lazy=True),
        order_by="Project.id",
        cascade_backrefs=False,
    )


class TokenSuperUser:
    @property
    def projects(self):
        return db.session.scalars(db.select(Project)).all()

    @property
    def magic_castles(self):
        return [
            MagicCastle(orm)
            for orm in db.session.scalars(db.select(MagicCastleORM)).all()
        ]


class User:
    __slots__ = ["orm", "username", "domain", "usertype", "public_keys"]

    def __init__(self, orm, username, domain, usertype, public_keys=[]):
        self.orm = orm
        self.username = username
        self.domain = domain
        self.usertype = usertype
        self.public_keys = public_keys

    @property
    def projects(self):
        return self.orm.projects

    @property
    def magic_castles(self):
        return [
            MagicCastle(orm=mc_orm)
            for project in self.projects
            for mc_orm in project.magic_castles
        ]


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
            orm=orm,
            username=username,
            domain="localhost",
            usertype="local",
            public_keys=public_keys,
        )


class SAMLUser(User):
    """
    User class for users created when the authentication type is set to SAML.

    An authenticated user can be an admin or a regular user. An admin can view
    and edit clusters created by anyone, while a regular user can only view and
    edit his own clusters.
    """

    __slots__ = ["scoped_id", "given_name", "surname", "mail"]

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
            domain=scope,
            usertype="saml",
            public_keys=ssh_public_key.split(";"),
        )
        self.scoped_id = edu_person_principal_name
        self.given_name = given_name
        self.surname = surname
        self.mail = mail
