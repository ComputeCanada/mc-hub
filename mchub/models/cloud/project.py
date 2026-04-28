import enum

from functools import partial

import marshmallow
from marshmallow import fields, EXCLUDE
from marshmallow.validate import URL, Length

from ...database import db


class Provider(str, enum.Enum):
    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"
    OPENSTACK = "openstack"
    OVH = "ovh"


project_admins = db.Table(
    "project_admins",
    db.Column("user_id", db.Integer, db.ForeignKey("user.id"), primary_key=True),
    db.Column("project_id", db.Integer, db.ForeignKey("project.id"), primary_key=True),
)


class Project(db.Model):
    __tablename__ = "project"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(), nullable=False)
    provider = db.Column(db.Enum(Provider), nullable=False)
    github_template = db.Column(db.String(), nullable=False)
    env = db.Column(db.PickleType())
    tfcloud_project_id = db.Column(db.String(), nullable=False)
    admins = db.relationship(
        "UserORM",
        secondary=project_admins,
        lazy="subquery",
        cascade_backrefs=False,
    )
    @property
    def members(self):
        seen = {u.id for u in self.admins}
        result = list(self.admins)
        for u in self._direct_members:
            if u.id not in seen:
                result.append(u)
        return result

    magic_castles = db.relationship(
        "MagicCastleORM",
        back_populates="project",
        cascade_backrefs=False,
        cascade="all, delete-orphan",
    )


class OpenStackEnv(marshmallow.Schema):
    OS_AUTH_URL = fields.String(required=True, validate=[URL()])
    OS_APPLICATION_CREDENTIAL_ID = fields.String(
        required=True, validate=[Length(min=32)]
    )
    OS_APPLICATION_CREDENTIAL_SECRET = fields.String(
        required=True, validate=[Length(min=86)]
    )


ENV_VALIDATORS = {
    Provider.OPENSTACK: partial(OpenStackEnv().load, unknown=EXCLUDE),
}