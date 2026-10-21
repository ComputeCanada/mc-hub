from ..database import db


class AgentHealthSnapshot(db.Model):
    __tablename__ = "agent_health_snapshot"
    organization = db.Column(db.String(255), primary_key=True)
    pool_name = db.Column(db.String(255), primary_key=True)
    checked_at = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(32), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notified_status = db.Column(db.String(32))
