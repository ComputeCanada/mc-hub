"""Project-visible resource intentions; cluster definitions remain owner-private."""
from ..database import db


class CapacityPlan(db.Model):
    __tablename__ = "capacity_plan"
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("project.id"), nullable=False, index=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    starts_at = db.Column(db.Float, nullable=False)
    ends_at = db.Column(db.Float, nullable=False)
    definition = db.Column(db.JSON, nullable=False)
    demand = db.Column(db.JSON, nullable=False)
    auto_create = db.Column(db.Boolean, nullable=False, default=False)
    status = db.Column(db.String(24), nullable=False, default="planned")
    message = db.Column(db.String(255))
    cluster_usage_id = db.Column(db.String(36))
    project = db.relationship("Project", backref=db.backref("capacity_plans", cascade="all, delete-orphan"))
    owner = db.relationship("UserORM")


class CapacityQuotaCheck(db.Model):
    __tablename__ = "capacity_quota_check"
    project_id = db.Column(db.Integer, db.ForeignKey("project.id"), primary_key=True)
    checked_at = db.Column(db.Float, nullable=False)
    next_check_at = db.Column(db.Float, nullable=False)
    input_signature = db.Column(db.String(64), nullable=False)
    notification_signature = db.Column(db.String(64))
    result = db.Column(db.JSON, nullable=False)
    project = db.relationship("Project", backref=db.backref("capacity_quota_checks", cascade="all, delete-orphan"))
