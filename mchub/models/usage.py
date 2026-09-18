"""Durable analytics snapshots: deliberately no cascading foreign keys."""
import datetime
import uuid

from ..database import db


def utcnow():
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)


def new_id():
    return str(uuid.uuid4())


class UsageState(db.Model):
    __tablename__ = "usage_state"
    id = db.Column(db.Integer, primary_key=True)
    tracking_started_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    last_poll_at = db.Column(db.DateTime)


class UsageLifetime(db.Model):
    __tablename__ = "usage_lifetime"
    id = db.Column(db.String(36), primary_key=True, default=new_id)
    cluster_id = db.Column(db.String(36), nullable=False, index=True)
    active_cluster_id = db.Column(db.String(36), unique=True)
    hostname = db.Column(db.String(256), nullable=False)
    project_id = db.Column(db.String(36), nullable=False)
    project_name = db.Column(db.String, nullable=False)
    provider = db.Column(db.String, nullable=False)
    creator = db.Column(db.String)
    repository = db.Column(db.String)
    predates_tracking = db.Column(db.Boolean, nullable=False, default=False)
    started_at = db.Column(db.DateTime)
    healthy_at = db.Column(db.DateTime)
    ended_at = db.Column(db.DateTime)


class UsageApply(db.Model):
    __tablename__ = "usage_apply"
    id = db.Column(db.Integer, primary_key=True)
    lifetime_id = db.Column(db.String(36), nullable=False, index=True)
    run_id = db.Column(db.String(256), nullable=False, unique=True)
    commit_sha = db.Column(db.String(64))
    initiated_by = db.Column(db.String)
    kind = db.Column(db.String(16), nullable=False)
    requested_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    applied_at = db.Column(db.DateTime)
    healthy_at = db.Column(db.DateTime)
    outcome = db.Column(db.String(24), nullable=False, default="pending")
