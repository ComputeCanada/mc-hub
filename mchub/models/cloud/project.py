import enum

from functools import partial

import marshmallow
from marshmallow import fields, ValidationError, EXCLUDE

from ...database import db


class Provider(enum.Enum):
    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"
    OPENSTACK = "openstack"
    OVH = "ovh"


class Project(db.Model):
    __tablename__ = "project"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(), nullable=False)
    provider = db.Column(db.Enum(Provider), nullable=False)
    env = db.Column(db.PickleType())


class OpenStackEnv(marshmallow.Schema):
    OS_AUTH_URL = fields.String(required=True)
    OS_APPLICATION_CREDENTIAL_ID = fields.String(required=True)
    OS_APPLICATION_CREDENTIAL_SECRET = fields.String(required=True)


ENV_VALIDATORS = {
    Provider.OPENSTACK: partial(OpenStackEnv().load, unknown=EXCLUDE),
}
