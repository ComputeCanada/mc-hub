from copy import deepcopy
from datetime import datetime, timedelta, timezone

from flask import request
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError

from .api_view import ApiView
from .usage_api import durations, iso
from ..database import db
from ..exceptions.invalid_usage_exception import InvalidUsageException
from ..models.benchmark import Benchmark, BenchmarkRun, SUCCESS_CRITERIA
from ..models.cloud.project import Project
from ..models.magic_castle.magic_castle import MagicCastle
from ..models.magic_castle.magic_castle_configuration import MagicCastleConfiguration
from ..models.user import User
from ..models.usage import utcnow
from ..services.benchmarks import (
    INTERVALS, enqueue, identity_locked, reserve_cluster_name, reusable_cluster,
    benchmark_lock, verify_empty,
)
from ..services.benchmark_setup import initialize_benchmark


def admin_projects(user):
    if not isinstance(user, User):
        raise InvalidUsageException("A project administrator account is required.", status_code=403)
    projects = [project for project in user.projects if user.is_project_admin(project)]
    if not projects:
        raise InvalidUsageException("You must administer at least one project to access benchmarks.", status_code=403)
    return projects


def authorize(user, benchmark):
    if benchmark is None or not any(
        project.id == benchmark.project_id and project.usage_id == benchmark.project_key
        for project in admin_projects(user)
    ):
        raise InvalidUsageException("Benchmark not found or project administrator access required.", status_code=403)


def definition(benchmark):
    active = db.session.scalar(db.select(BenchmarkRun).filter_by(active_benchmark_id=benchmark.id))
    return {
        "id": benchmark.id, "project_id": benchmark.project_id, "name": benchmark.name,
        "frequency": benchmark.frequency, "timeout_minutes": benchmark.timeout_minutes,
        "success_criterion": benchmark.success_criterion,
        "enabled": benchmark.enabled, "archived": benchmark.archived,
        "next_run_at": iso(benchmark.next_run_at), "revision": benchmark.revision,
        "configuration": benchmark.configuration,
        "identity_locked": identity_locked(benchmark),
        "setup_status": benchmark.setup_status, "setup_error": benchmark.setup_error,
        "active_run": active.phase if active else None,
    }


def run_result(run):
    # Results expose infrastructure specs, not guest credentials or hieradata.
    specs = {key: value for key, value in run.configuration.items()
             if key not in ("guest_passwd", "hieradata", "hieradata_entries", "public_keys")}
    return {
        "id": run.id, "revision": run.revision, "hostname": run.hostname,
        "configuration": specs, "phase": run.phase, "outcome": run.outcome,
        "requested_at": iso(run.requested_at), "applied_at": iso(run.applied_at),
        "apply_started_at": iso(run.apply_started_at), "measurement_started_at": iso(run.measurement_started_at),
        "healthy_at": iso(run.healthy_at), "cleanup_at": iso(run.cleanup_at),
        "success_criterion": run.success_criterion, "target_reached_at": iso(run.target_reached_at),
        "error": run.error, "cleanup_error": run.cleanup_error,
        "terraform_run_id": run.terraform_run_id, "commit_sha": run.commit_sha,
        "repository": run.repository,
        "duration_seconds": run.duration_seconds,
    }


def comparison_groups(runs):
    """Keep commits, repositories, and target states separate across all history."""
    groups = {}
    for run in runs:
        if not run.commit_sha:
            continue  # An unknown commit is never evidence of comparability.
        key = (run.repository, run.commit_sha, run.success_criterion)
        groups.setdefault(key, []).append(run)
    result = []
    for (repository, sha, criterion), members in groups.items():
        timed = [r.duration_seconds for r in members
                 if r.outcome == "successful" and r.duration_seconds is not None]
        completed = [r for r in members if r.outcome in ("successful", "failed", "timed_out")]
        result.append({
            "id": f"{repository or ''}@{sha}:{criterion}",
            "repository": repository, "commit_sha": sha, "success_criterion": criterion,
            "total_runs": len(members), "timing": durations(timed),
            "success_rate": sum(r.outcome == "successful" for r in completed) / len(completed) if completed else None,
        })
    return result


def update_definition(benchmark, payload, user, creating=False):
    if not isinstance(payload, dict):
        raise InvalidUsageException("Provide a benchmark definition.")
    name = payload.get("name", "").strip() if isinstance(payload.get("name"), str) else ""
    frequency = payload.get("frequency")
    timeout = payload.get("timeout_minutes")
    criterion = payload.get("success_criterion", benchmark.success_criterion or "healthy")
    enabled = payload.get("enabled")
    config = payload.get("configuration")
    project = next((p for p in admin_projects(user) if p.id == payload.get("project_id")), None)
    if project is None:
        raise InvalidUsageException("Choose a project you administer.", status_code=403)
    if not creating and (project.id != benchmark.project_id or project.usage_id != benchmark.project_key):
        raise InvalidUsageException("A benchmark cannot change project.")
    if not name or len(name) > 120 or not isinstance(frequency, str) or frequency not in INTERVALS:
        raise InvalidUsageException("Provide a name (up to 120 characters) and an hourly, daily or weekly schedule.")
    if type(timeout) is not int or not 10 <= timeout <= 1440 or type(enabled) is not bool:
        raise InvalidUsageException("Timeout must be 10–1440 minutes; enabled must be true or false.")
    if not isinstance(criterion, str) or criterion not in SUCCESS_CRITERIA:
        raise InvalidUsageException("Success criterion must be build_completed or healthy.")
    if not isinstance(config, dict):
        raise InvalidUsageException("Provide cluster specifications.")
    config = deepcopy(config)
    config["cloud"] = {"id": project.id, "name": project.name}
    config["expiration_date"] = None
    # The shared form supplies hieradata entries; creation encrypts them per cluster.
    try:
        MagicCastleConfiguration(project.provider, config)
    except (ValidationError, TypeError, ValueError):
        raise InvalidUsageException("Invalid cluster specifications.")
    reserve_cluster_name(benchmark, config)
    MagicCastle.validate_creation_version(config)
    if not config.get("instances") or any(
        not isinstance(instance, dict) or type(instance.get("count")) is not int
        or instance["count"] < 0 or not instance.get("type")
        for instance in config["instances"].values()
    ):
        raise InvalidUsageException("Provide valid instance types and nonnegative integer counts.")
    next_at = payload.get("next_run_at")
    try:
        if next_at:
            next_at = datetime.fromisoformat(next_at.replace("Z", "+00:00"))
            if next_at.tzinfo is None:
                next_at = next_at.replace(tzinfo=timezone.utc)
            next_at = next_at.astimezone(timezone.utc).replace(tzinfo=None)
        else:
            next_at = utcnow() + timedelta(seconds=INTERVALS[frequency])
    except (ValueError, TypeError, AttributeError, OverflowError):
        raise InvalidUsageException("Provide a valid next run timestamp in UTC.")
    benchmark.name, benchmark.frequency = name, frequency
    benchmark.configuration, benchmark.timeout_minutes = config, timeout
    benchmark.success_criterion = criterion
    benchmark.enabled, benchmark.next_run_at = enabled, next_at
    if creating:
        benchmark.project_id, benchmark.project_key = project.id, project.usage_id
        benchmark.created_by = user.orm.scoped_id
    else:
        benchmark.revision += 1


def commit_definition():
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise InvalidUsageException("This cluster name is already reserved by another benchmark. Choose another name.", status_code=409)


class BenchmarkAPI(ApiView):
    def get(self, user, benchmark_id=None):
        projects = admin_projects(user)
        if benchmark_id is None:
            keys = {p.usage_id for p in projects}
            benchmarks = db.session.scalars(db.select(Benchmark).where(
                Benchmark.project_key.in_(keys),
            ).order_by(Benchmark.created_at.desc())).all()
            return {"projects": [{"id": p.id, "name": p.name} for p in projects],
                    "benchmarks": [definition(b) for b in benchmarks]}
        benchmark = db.session.get(Benchmark, benchmark_id)
        authorize(user, benchmark)
        runs = list(db.session.scalars(db.select(BenchmarkRun).filter_by(benchmark_id=benchmark_id)
                                      .order_by(BenchmarkRun.requested_at.desc())))
        groups = comparison_groups(runs)
        # Default to the latest measured commit with the definition's current
        # target; the dashboard can also inspect each older group independently.
        selected = next((g for g in groups if g["success_criterion"] == benchmark.success_criterion), None)
        return {"benchmark": definition(benchmark), "runs": [run_result(r) for r in runs[:500]],
                "total_runs": len(runs), "comparison_groups": groups,
                "default_comparison_group": selected["id"] if selected else None,
                "unassigned_runs": sum(not r.commit_sha for r in runs),
                "timing": selected["timing"] if selected else durations([]),
                "success_rate": selected["success_rate"] if selected else None}

    def post(self, user, benchmark_id=None):
        if benchmark_id:
            benchmark = db.session.get(Benchmark, benchmark_id)
            authorize(user, benchmark)
            run = enqueue(benchmark, user.orm.scoped_id)
            db.session.commit()
            return {"id": run.id}, 202
        benchmark = Benchmark()
        update_definition(benchmark, request.get_json(), user, creating=True)
        db.session.add(benchmark)
        commit_definition()
        with benchmark_lock(benchmark.id):
            if not initialize_benchmark(benchmark):
                return {"message": benchmark.setup_error, "benchmark": definition(benchmark)}, 502
        return definition(benchmark), 201

    def put(self, user, benchmark_id):
        benchmark = db.session.get(Benchmark, benchmark_id)
        authorize(user, benchmark)
        with benchmark_lock(benchmark.id):
            db.session.refresh(benchmark)
            if benchmark.archived:
                raise InvalidUsageException("Archived benchmarks cannot be edited.", status_code=409)
            update_definition(benchmark, request.get_json(), user)
            commit_definition()
            if not initialize_benchmark(benchmark):
                return {"message": benchmark.setup_error, "benchmark": definition(benchmark)}, 502
        return definition(benchmark)

    def patch(self, user, benchmark_id):
        benchmark = db.session.get(Benchmark, benchmark_id)
        authorize(user, benchmark)
        data = request.get_json()
        if not isinstance(data, dict) or type(data.get("enabled")) is not bool:
            raise InvalidUsageException("Provide enabled as true or false.")
        if benchmark.archived:
            raise InvalidUsageException("Archived benchmarks cannot be scheduled.", status_code=409)
        benchmark.enabled = data["enabled"]
        db.session.commit()
        return definition(benchmark)

    def delete(self, user, benchmark_id):
        benchmark = db.session.get(Benchmark, benchmark_id)
        authorize(user, benchmark)
        with benchmark_lock(benchmark.id):
            db.session.refresh(benchmark)
            active = db.session.scalar(db.select(BenchmarkRun).filter_by(active_benchmark_id=benchmark.id))
            retained = reusable_cluster(benchmark.id)
            if active is None and retained is not None:
                if retained.benchmark_run_id is None:
                    # A saved definition has no measurement run to own cleanup.
                    # Setup never applies resources; verify and archive it here.
                    cluster = MagicCastle(retained)
                    verify_empty(cluster)
                    cluster.complete_teardown()
                    cluster.destroy_empty_cluster()
                else:
                    # Reuse the last run's cleanup task to archive retained integrations.
                    previous = db.session.get(BenchmarkRun, retained.benchmark_run_id)
                    previous.phase, previous.active_benchmark_id = "cleanup", benchmark.id
                    previous.cleanup_at, previous.next_attempt_at = None, utcnow()
            benchmark.archived, benchmark.enabled = True, False
            db.session.commit()
        return {}, 204
