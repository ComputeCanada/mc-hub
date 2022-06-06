import enum

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
