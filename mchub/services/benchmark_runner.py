"""Durable benchmark state machine with bounded, isolated lifecycle operations."""
import argparse
from copy import deepcopy
from datetime import timedelta
import logging
import os
import signal
import subprocess
import sys
import time
from threading import Event, Thread

from sqlalchemy import case

from .. import create_app
from ..database import db
from ..models.benchmark import Benchmark, BenchmarkRun
from ..models.cloud.project import Project
from ..models.cloud.aws_manager import ensure_aws_feasible
from ..models.magic_castle.magic_castle import MagicCastle, MagicCastleORM
from ..models.magic_castle.cluster_status_code import ClusterStatusCode as Status
from ..models.usage import UsageApply, utcnow
from ..models.user import UserORM
from ..exceptions.invalid_usage_exception import InvalidUsageException
from .benchmarks import schedule_due, reusable_cluster, benchmark_lock
from . import cluster_lifecycle as lifecycle
from .terraform_cloud_api import get_terraform_cloud, TerraformCloudVariable, TFCloudStatusCode
from .worker_logging import configure_worker_logging

logger = logging.getLogger(__name__)
POLL_INTERVAL = 10
STEP_TIMEOUT = 300
MAX_OPERATIONS = 4


def finish(run, outcome, message=None):
    orm = cluster_for(run)
    if orm is not None and run.phase == "creating":
        orm.status = Status.PLAN_ERROR
    run.outcome, run.error = outcome, message
    run.finished_at, run.phase = utcnow(), "cleanup"
    run.next_attempt_at = utcnow()
    db.session.commit()


def cluster_for(run):
    owned = db.session.scalar(db.select(MagicCastleORM).filter_by(benchmark_run_id=run.id))
    if owned is None and run.reuse_cluster:
        owned = reusable_cluster(run.benchmark_id)
    return owned


def refresh_measurement(run, orm):
    if orm is not None:
        run.repository = orm.usage_repository
        if run.terraform_run_id is None and orm.tfcloud_run and orm.tfcloud_run.run_id:
            run.terraform_run_id = orm.tfcloud_run.run_id
            if orm.tfcloud_run.commit_sha:
                run.commit_sha = orm.tfcloud_run.commit_sha
    attempt = db.session.scalar(db.select(UsageApply).filter_by(run_id=run.terraform_run_id)) if run.terraform_run_id else None
    if attempt:
        run.applied_at, run.healthy_at = attempt.applied_at, attempt.healthy_at
    db.session.commit()


def perform(orm, target, *args):
    lifecycle.claim_background_task(orm, owner="benchmark")
    return lifecycle.execute_claimed_task(orm.hostname, target, *args)


def verify_empty(cluster):
    if cluster.tfcloud_workspace:
        tf = get_terraform_cloud()
        tf.discard_workspace_plans(cluster.tfcloud_workspace)
        tf.verify_workspace_empty(cluster.tfcloud_workspace)
    elif cluster.tf_state is not None:
        raise InvalidUsageException("Cannot verify benchmark resources without a Terraform workspace.")


def prepare_run(run, orm, creator):
    if orm is None:
        benchmark = db.session.get(Benchmark, run.benchmark_id)
        if run.reuse_cluster and benchmark.setup_status != "pending":
            raise InvalidUsageException("Benchmark integrations are missing. Save the benchmark to set them up before running it.")
        MagicCastle().plan_creation(deepcopy(run.configuration), creator,
                                   benchmark_run_id=run.id, timeout=STEP_TIMEOUT - 10)
        return
    if orm.hostname != run.hostname or orm.project_id != run.configuration["cloud"]["id"]:
        raise InvalidUsageException("The benchmark cluster identity does not match this run.")
    cluster = MagicCastle(orm)
    if not orm.undeployed or cluster.is_busy:
        raise InvalidUsageException("Finish benchmark cleanup before rebuilding.")
    verify_empty(cluster)
    cluster.complete_teardown()
    orm.benchmark_run_id = run.id
    if run.reuse_cluster:
        orm.benchmark_id = run.benchmark_id
    db.session.commit()
    if not (orm.usage_repository and orm.tfcloud_workspace and orm.eyaml_public_key):
        # Retry incomplete initial setup using every integration already recorded.
        cluster.plan_creation(deepcopy(run.configuration), creator, benchmark_run_id=run.id,
                              timeout=STEP_TIMEOUT - 10, reuse_integrations=True)
    else:
        # Autoscaling may have changed this workspace variable during the last run.
        get_terraform_cloud().upsert_workspace_variable_set(orm.tfcloud_workspace, [
            TerraformCloudVariable(name="pool", value="[]", sensitive=False, hcl=True, category="terraform"),
        ])
        perform(orm, cluster.plan_benchmark_run, run.configuration, STEP_TIMEOUT - 10)


def cleanup(run, orm):
    if orm is None:
        run.phase, run.active_benchmark_id = "complete", None
        run.cleanup_at, run.cleanup_error = utcnow(), None
        db.session.commit()
        return
    cluster = MagicCastle(orm)
    if orm.tfcloud_run.run_id and cluster.plan is None:
        plan = get_terraform_cloud().get_run_plan_log_json(orm.tfcloud_run.run_id)
        if plan is not None:
            cluster.plan = plan
    status = cluster.status
    if cluster.is_busy or orm.status == Status.BACKGROUND_TASK_RUNNING:
        run.cleanup_error = "Waiting for the current Terraform operation to finish before cleanup."
        return
    if orm.undeployed or status == Status.NOT_DEPLOYED:
        benchmark = db.session.get(Benchmark, run.benchmark_id)
        if run.reuse_cluster and benchmark is not None and not benchmark.archived:
            verify_empty(cluster)
            cluster.complete_teardown()
        else:
            perform(orm, cluster.destroy_empty_cluster)
        cleanup(run, None)
        return
    tf = get_terraform_cloud()
    run_id = orm.tfcloud_run.run_id
    is_destroy = False
    if run_id:
        _, is_destroy = tf.get_run_status(run_id)
    if status == Status.CREATED and is_destroy:
        lifecycle.validate_apply(orm)
        perform(orm, lifecycle.apply_cluster, orm.hostname, None, run_id)
    else:
        if status == Status.CREATED and run_id:
            tf.discard_run(run_id)
        perform(orm, lifecycle.plan_teardown, orm.hostname, STEP_TIMEOUT - 10)
    run.cleanup_error = None


def advance_run(run_id):
    run = db.session.get(BenchmarkRun, run_id)
    if run is None or run.phase == "complete":
        return
    orm = cluster_for(run)
    # A previous operation process may have died while holding this claim.
    # The per-benchmark file lock guarantees it is no longer executing locally.
    if orm is not None and orm.status == Status.BACKGROUND_TASK_RUNNING and orm.creation_step == "benchmark":
        orm.status = Status.PLAN_ERROR
        orm.creation_step = None
        db.session.commit()
    if run.phase == "cleanup":
        cleanup(run, orm)
    elif run.phase == "queued":
        benchmark = db.session.get(Benchmark, run.benchmark_id)
        if benchmark is not None and benchmark.archived:
            finish(run, "cancelled", "Benchmark archived before this run started.")
            return
        project = db.session.get(Project, benchmark.project_id) if benchmark else None
        if project is None or project.usage_id != benchmark.project_key:
            finish(run, "failed", "The benchmark project is no longer available.")
            return
        run.phase, run.started_at = "creating", utcnow()
        db.session.commit()
        ensure_aws_feasible(project, run.configuration)
        creator = db.session.scalar(db.select(UserORM).filter_by(scoped_id=benchmark.created_by))
        prepare_run(run, orm, creator.id if creator else None)
        if run.reuse_cluster:
            benchmark.setup_status, benchmark.setup_error = "ready", None
        orm = cluster_for(run)
        refresh_measurement(run, orm)
        run.phase = "ready"
    elif run.phase == "creating":
        finish(run, "failed", "Cluster creation was interrupted; cleaning up before another run.")
        return
    else:
        if orm is None:
            finish(run, "failed", "Benchmark cluster is unavailable.")
            return
        cluster = MagicCastle(orm)
        refresh_measurement(run, orm)
        if run.success_criterion == "build_completed":
            # Inspect the original deployment run directly: status also probes
            # service health, which this target does not require.
            remote, is_destroy = (
                get_terraform_cloud().get_run_status(run.terraform_run_id)
                if run.terraform_run_id else (None, None)
            )
            status = Status.from_tfcloudstatus(remote, is_destroy)
            if is_destroy is False and remote == TFCloudStatusCode.PLANNED_AND_FINISHED:
                finish(run, "failed", "Terraform completed without an apply; no build was measured.")
                return
            if is_destroy is False and remote == TFCloudStatusCode.APPLIED and run.apply_started_at is None:
                started, finished = get_terraform_cloud().get_apply_timestamps(run.terraform_run_id)
                if started is not None and finished is not None:
                    run.apply_started_at, run.target_reached_at = started, finished
        else:
            status = cluster.status
            refresh_measurement(run, orm)
            if run.target_reached_at is None:
                run.target_reached_at = run.healthy_at
        db.session.commit()
        deadline = run.started_at + timedelta(minutes=run.timeout_minutes)
        measured_target = run.target_reached_at
        if run.success_criterion == "build_completed" and run.apply_started_at is None:
            measured_target = None  # An older local observation is not an apply timestamp.
        if measured_target and measured_target <= deadline:
            finish(run, "successful")
            return
        if utcnow() >= deadline:
            finish(run, "timed_out", "The benchmark exceeded its maximum run time.")
            return
        if status in (Status.PLAN_ERROR, Status.BUILD_ERROR, Status.PROVISIONING_ERROR):
            finish(run, "failed", f"Deployment reported {status.value}.")
            return
        if run.phase == "ready":
            lifecycle.validate_apply(orm)
            ensure_aws_feasible(orm.project, cluster.config, cluster.aws_resource_ids if orm.project.provider == "aws" else None)
            run.phase = "applying"
            db.session.commit()  # Never replay an apply with unknown acceptance.
            perform(orm, lifecycle.apply_cluster, orm.hostname, run.requested_by)
            refresh_measurement(run, orm)
            run.phase = "waiting"
        elif run.phase == "applying":
            run.phase = "waiting"
    run.next_attempt_at = utcnow() + timedelta(seconds=POLL_INTERVAL)
    db.session.commit()


def record_error(run_id, message):
    db.session.rollback()
    run = db.session.get(BenchmarkRun, run_id)
    if run is None or run.phase == "complete":
        return
    if run.phase == "cleanup":
        run.cleanup_error = message
        run.next_attempt_at = utcnow() + timedelta(seconds=60)
        db.session.commit()
    else:
        outcome = "timed_out" if run.started_at and utcnow() >= run.started_at + timedelta(minutes=run.timeout_minutes) else "failed"
        finish(run, outcome, message)


def step_main(run_id, parent_pid):
    # A supervisor restart must not leave an orphan still modifying resources.
    def watch_parent():
        while True:
            if os.getppid() != parent_pid:
                os._exit(1)
            time.sleep(1)
    Thread(target=watch_parent, daemon=True).start()
    app = create_app()
    with app.app_context():
        run = db.session.get(BenchmarkRun, run_id)
        if run is None:
            return
        try:
            with benchmark_lock(run.benchmark_id):
                try:
                    advance_run(run_id)
                except Exception:
                    logger.exception("Benchmark operation failed for %s", run_id)
                    # External errors can contain credentials; expose a generic message.
                    record_error(run_id, "Operation failed. See background-worker logs; cleanup will retry automatically.")
        except InvalidUsageException:
            return


def stop_process(process):
    if process.poll() is None:
        process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def main():
    app = create_app()
    stopping = Event()
    children = {}
    for signum in (signal.SIGTERM, signal.SIGINT):
        signal.signal(signum, lambda *_: stopping.set())
    try:
        while not stopping.is_set():
            with app.app_context():
                try:
                    for run_id, (process, deadline) in list(children.items()):
                        if process.poll() is not None or time.monotonic() >= deadline:
                            timed_out = process.poll() is None
                            stop_process(process)
                            if timed_out or process.returncode:
                                record_error(run_id, "Operation timed out or was interrupted; cleanup will retry automatically.")
                            del children[run_id]
                    schedule_due()
                    due = db.session.scalars(db.select(BenchmarkRun).where(
                        BenchmarkRun.phase != "complete", BenchmarkRun.next_attempt_at <= utcnow(),
                    ).order_by(case((BenchmarkRun.phase == "cleanup", 0),
                                    (BenchmarkRun.phase.in_(["waiting", "applying"]), 1), else_=2),
                               BenchmarkRun.next_attempt_at)).all()
                    for run in due:
                        if len(children) >= MAX_OPERATIONS or stopping.is_set():
                            break
                        if run.id in children:
                            continue
                        timeout = STEP_TIMEOUT
                        # A build may have finished before its deadline while the
                        # worker was unavailable. Allow the bounded observation
                        # step to read Terraform's completion time before expiring it.
                        checking_build = run.success_criterion == "build_completed" and run.phase in ("waiting", "applying")
                        if run.started_at and run.phase != "cleanup" and not checking_build:
                            timeout = min(timeout, max(1, (run.started_at + timedelta(minutes=run.timeout_minutes) - utcnow()).total_seconds()))
                        process = subprocess.Popen([sys.executable, "-m", "mchub.services.benchmark_runner", "--step", run.id, "--parent", str(os.getpid())])
                        children[run.id] = (process, time.monotonic() + timeout)
                except Exception:
                    db.session.rollback()
                    logger.exception("Benchmark scheduler sweep failed")
            stopping.wait(POLL_INTERVAL)
    finally:
        for process, _ in children.values():
            stop_process(process)


if __name__ == "__main__":
    configure_worker_logging()
    parser = argparse.ArgumentParser()
    parser.add_argument("--step")
    parser.add_argument("--parent", type=int)
    args = parser.parse_args()
    if args.step:
        if args.parent is None:
            parser.error("--step requires --parent")
        step_main(args.step, args.parent)
    else:
        main()
