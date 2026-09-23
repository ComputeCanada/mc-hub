"""Durable events and independent destination deliveries."""
from ..database import db


class NotificationEvent(db.Model):
    __tablename__ = "notification_event"
    id = db.Column(db.String(36), primary_key=True)
    event_type = db.Column(db.String(100), nullable=False)
    resource_id = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.Float, nullable=False)
    payload = db.Column(db.JSON, nullable=False)


class NotificationDelivery(db.Model):
    __tablename__ = "notification_delivery"
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.String(36), db.ForeignKey("notification_event.id"), nullable=False)
    destination_id = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(20), nullable=False, default="pending")
    attempts = db.Column(db.Integer, nullable=False, default=0)
    next_attempt_at = db.Column(db.Float, nullable=False)
    delivered_at = db.Column(db.Float)
    last_error = db.Column(db.String(255))
    event = db.relationship(NotificationEvent)
    __table_args__ = (
        db.UniqueConstraint("event_id", "destination_id", name="uq_notification_destination"),
        db.Index("ix_notification_due", "state", "next_attempt_at"),
    )
