from ..database import db


class TerraformCloudRunORM(db.Model):
    __tablename__ = "terraformcloudrun"
    id = db.Column(db.Integer, primary_key=True)
    run_id = db.Column(db.String(256))
    plan = db.Column(db.PickleType())
    apply_log_url = db.Column(db.String)
    tf_state = db.Column(db.PickleType())
    magic_castle = db.relationship("MagicCastleORM", back_populates="tfcloud_run")
    magic_castle_id = db.Column(db.Integer, db.ForeignKey("magiccastle.id"))