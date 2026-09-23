from ..database import db


class ServiceStatusSnapshot(db.Model):
    __tablename__ = "service_status_snapshot"
    provider = db.Column(db.String(100), primary_key=True)
    last_success_at = db.Column(db.Float)
    last_attempt_at = db.Column(db.Float)
    last_attempt_ok = db.Column(db.Boolean)
    snapshot = db.Column(db.JSON)
    notification_snapshot = db.Column(db.JSON)
