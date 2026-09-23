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
