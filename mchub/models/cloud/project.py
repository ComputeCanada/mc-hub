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


class Project(db.Model):
    __tablename__ = "project"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(), nullable=False)
    admin_id = db.Column(db.Integer, nullable=False)
    provider = db.Column(db.Enum(Provider), nullable=False)
    env = db.Column(db.PickleType())
    magic_castles = db.relationship(
        "MagicCastleORM",
        back_populates="project",
        cascade_backrefs=False,
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
