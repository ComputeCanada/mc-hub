"""Benchmark scheduling, integration ownership, and run allocation."""
from contextlib import contextmanager
from copy import deepcopy
from datetime import timedelta
import fcntl
from pathlib import Path

from sqlalchemy.exc import IntegrityError

from ..database import db
from ..configuration.env import DATABASE_PATH
from ..exceptions.invalid_usage_exception import InvalidUsageException
from ..models.benchmark import Benchmark, BenchmarkRun
from ..models.magic_castle.magic_castle import MagicCastleORM
from .terraform_cloud_api import get_terraform_cloud
from ..models.usage import new_id, utcnow

INTERVALS = {"hourly": 3600, "daily": 86400, "weekly": 604800}
MAX_INTERNAL_HOSTNAME_LENGTH = 63


@contextmanager
def benchmark_lock(benchmark_id):
    with (Path(DATABASE_PATH) / f"benchmark-{benchmark_id}.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise InvalidUsageException("This benchmark is busy. Wait for its current operation to finish.", status_code=409)
        yield


def validate_cluster_identity(config):
    if len(f"{config['cluster_name']}.int.{config['domain']}") > MAX_INTERNAL_HOSTNAME_LENGTH:
        raise InvalidUsageException(
            "{cluster_name}.int.{domain} must be at most 63 characters, "
            "so choose a shorter cluster name or domain."
        )


def identity_locked(benchmark):
    if benchmark.setup_status in ("creating", "ready", "failed"):
        return True
    return db.session.scalar(db.select(BenchmarkRun.id).where(
        BenchmarkRun.benchmark_id == benchmark.id, BenchmarkRun.reuse_cluster.is_(True),
    ).limit(1)) is not None


def reserve_cluster_name(benchmark, config):
    validate_cluster_identity(config)
    if identity_locked(benchmark) and any(
        config[key] != benchmark.configuration[key] for key in ("cluster_name", "domain")
    ):
        raise InvalidUsageException("Keep the cluster name and domain after benchmark setup starts. Create a new benchmark to change them.")
    name = config["cluster_name"]
    reserved = db.session.scalar(db.select(Benchmark).filter_by(cluster_name=name))
    if reserved is not None and reserved.id != benchmark.id:
        raise InvalidUsageException("This cluster name is reserved by another benchmark. Choose another name.", status_code=409)
    owned_runs = db.select(BenchmarkRun.id).where(
        BenchmarkRun.benchmark_id == benchmark.id, BenchmarkRun.reuse_cluster.is_(True),
    )
    collision = db.session.scalar(db.select(MagicCastleORM.id).where(
        MagicCastleORM.hostname.startswith(f"{name}.", autoescape=True),
        db.or_(MagicCastleORM.benchmark_id.is_(None), MagicCastleORM.benchmark_id != benchmark.id),
        db.or_(MagicCastleORM.benchmark_run_id.is_(None), MagicCastleORM.benchmark_run_id.not_in(owned_runs)),
    ).limit(1))
    if collision is not None:
        raise InvalidUsageException("This cluster name is already in use. Choose another name.", status_code=409)
    benchmark.cluster_name = name


def reusable_cluster(benchmark_id):
    initialized = db.session.scalar(db.select(MagicCastleORM).filter_by(benchmark_id=benchmark_id))
    if initialized is not None:
        return initialized
    return db.session.scalar(db.select(MagicCastleORM).join(
        BenchmarkRun, BenchmarkRun.id == MagicCastleORM.benchmark_run_id,
    ).where(BenchmarkRun.benchmark_id == benchmark_id, BenchmarkRun.reuse_cluster.is_(True)))


def verify_empty(cluster):
    if cluster.tfcloud_workspace:
        tf = get_terraform_cloud()
        tf.discard_workspace_plans(cluster.tfcloud_workspace)
        tf.verify_workspace_empty(cluster.tfcloud_workspace)
    elif cluster.tf_state is not None:
        raise InvalidUsageException("Cannot verify benchmark resources without a Terraform workspace.")


def enqueue(benchmark, actor=None):
    with benchmark_lock(benchmark.id):
        db.session.flush()
        db.session.refresh(benchmark)
        return _enqueue(benchmark, actor)


def _enqueue(benchmark, actor):
    if benchmark.archived:
        raise InvalidUsageException("This benchmark is archived.", status_code=409)
    if benchmark.setup_status != "ready":
        raise InvalidUsageException("Save the benchmark to complete its repository and workspace setup before running it.", status_code=409)
    reserve_cluster_name(benchmark, benchmark.configuration)
    run_id = new_id()
    specs = deepcopy(benchmark.configuration)
    specs["cloud"] = {"id": benchmark.project_id}
    specs["expiration_date"] = None
    run = BenchmarkRun(
        id=run_id, benchmark_id=benchmark.id, active_benchmark_id=benchmark.id,
        configuration=specs, revision=benchmark.revision,
        timeout_minutes=benchmark.timeout_minutes,
        success_criterion=benchmark.success_criterion,
        hostname=f"{specs['cluster_name']}.{specs['domain']}", requested_by=actor,
    )
    try:
        with db.session.begin_nested():
            db.session.add(run)
            db.session.flush()
    except IntegrityError:
        if not db.session.is_active:
            db.session.rollback()
        raise InvalidUsageException("A run is active, awaiting cleanup, or the cluster name is already reserved.", status_code=409)
    return run


def schedule_due():
    now = utcnow()
    due = list(db.session.scalars(db.select(Benchmark).where(
        Benchmark.enabled.is_(True), Benchmark.archived.is_(False), Benchmark.setup_status == "ready", Benchmark.next_run_at <= now,
    )))
    for benchmark in due:
        # Coalesce missed schedules; never launch a backlog after downtime.
        next_at = now + timedelta(seconds=INTERVALS[benchmark.frequency])
        claimed = db.session.execute(db.update(Benchmark).where(
            Benchmark.id == benchmark.id, Benchmark.next_run_at == benchmark.next_run_at,
            Benchmark.enabled.is_(True), Benchmark.archived.is_(False), Benchmark.setup_status == "ready",
        ).values(next_run_at=next_at).execution_options(synchronize_session=False))
        if claimed.rowcount == 1:
            try:
                enqueue(benchmark)
            except InvalidUsageException:
                pass  # An earlier run still owns this benchmark.
        db.session.commit()
