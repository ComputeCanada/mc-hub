"""Project-owned benchmark definitions and immutable run snapshots."""
from ..database import db
from .usage import new_id, utcnow

SUCCESS_CRITERIA = ("build_completed", "healthy")


class Benchmark(db.Model):
    __tablename__ = "benchmark"
    id = db.Column(db.String(36), primary_key=True, default=new_id)
    project_id = db.Column(db.Integer, nullable=False, index=True)
    project_key = db.Column(db.String(36), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    configuration = db.Column(db.JSON, nullable=False)
    # Reserved globally because Terraform workspace names share an organization.
    cluster_name = db.Column(db.String(63))
    setup_status = db.Column(db.String(16), nullable=False, default="pending", server_default="pending")
    setup_error = db.Column(db.String)
    __table_args__ = (db.Index("uq_benchmark_cluster_name", "cluster_name", unique=True),)
    frequency = db.Column(db.String(16), nullable=False)
    timeout_minutes = db.Column(db.Integer, nullable=False)
    success_criterion = db.Column(db.String(24), nullable=False, default="healthy", server_default="healthy")
    enabled = db.Column(db.Boolean, nullable=False, default=True)
    archived = db.Column(db.Boolean, nullable=False, default=False)
    next_run_at = db.Column(db.DateTime, nullable=False)
    created_by = db.Column(db.String, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    revision = db.Column(db.Integer, nullable=False, default=1)


class BenchmarkRun(db.Model):
    __tablename__ = "benchmark_run"
    id = db.Column(db.String(36), primary_key=True, default=new_id)
    benchmark_id = db.Column(db.String(36), nullable=False, index=True)
    # Released only after verified resource teardown.
    active_benchmark_id = db.Column(db.String(36), unique=True)
    configuration = db.Column(db.JSON, nullable=False)
    revision = db.Column(db.Integer, nullable=False)
    timeout_minutes = db.Column(db.Integer, nullable=False)
    success_criterion = db.Column(db.String(24), nullable=False, default="healthy", server_default="healthy")
    hostname = db.Column(db.String(256), nullable=False)
    # Existing runs keep the former per-run cleanup policy during upgrades.
    reuse_cluster = db.Column(db.Boolean, nullable=False, default=True, server_default="0")
    requested_by = db.Column(db.String)
    requested_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    started_at = db.Column(db.DateTime)
    applied_at = db.Column(db.DateTime)
    healthy_at = db.Column(db.DateTime)
    target_reached_at = db.Column(db.DateTime)
    finished_at = db.Column(db.DateTime)
    cleanup_at = db.Column(db.DateTime)
    next_attempt_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    phase = db.Column(db.String(24), nullable=False, default="queued")
    outcome = db.Column(db.String(24))
    error = db.Column(db.String)
    cleanup_error = db.Column(db.String)
    terraform_run_id = db.Column(db.String(256))
    commit_sha = db.Column(db.String(64))
    repository = db.Column(db.String)

    @property
    def duration_seconds(self):
        if self.applied_at and self.target_reached_at:
            return (self.target_reached_at - self.applied_at).total_seconds()
        return None
