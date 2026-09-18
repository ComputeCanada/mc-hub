"""Record lifecycle observations independently of mutable cluster definitions."""
from sqlalchemy.exc import IntegrityError
from ..database import db
from ..models.usage import UsageApply, UsageLifetime, UsageState, utcnow
from ..models.magic_castle.cluster_status_code import ClusterStatusCode as Status

POLL_INTERVAL = 30


def state():
    value = db.session.get(UsageState, 1)
    if value is None:
        value = UsageState(id=1)
        db.session.add(value)
        db.session.flush()
    return value


def current_lifetime(orm):
    return db.session.scalar(db.select(UsageLifetime).where(
        UsageLifetime.cluster_id == orm.usage_id,
        UsageLifetime.ended_at.is_(None),
    ))


def ensure_lifetime(orm):
    state()
    lifetime = current_lifetime(orm)
    if lifetime is None:
        # An existing deployment has an unknown start; never invent historical usage.
        legacy = orm.usage_legacy and not orm.undeployed
        lifetime = UsageLifetime(
            cluster_id=orm.usage_id, active_cluster_id=orm.usage_id, hostname=orm.hostname,
            project_id=orm.project.usage_id, project_name=orm.project.name,
            provider=orm.project.provider, creator=orm.created_by.scoped_id if orm.created_by else None,
            repository=orm.usage_repository, predates_tracking=legacy,
        )
        try:
            with db.session.begin_nested():
                db.session.add(lifetime)
                db.session.flush()
        except IntegrityError:
            lifetime = current_lifetime(orm)
            if lifetime is None:
                raise
    return lifetime


def begin_apply(orm, initiated_by=None):
    existing = db.session.scalar(db.select(UsageApply).filter_by(run_id=orm.tfcloud_run.run_id))
    if existing:
        return existing
    lifetime = ensure_lifetime(orm)
    db.session.execute(db.update(UsageApply).where(
        UsageApply.lifetime_id == lifetime.id,
        UsageApply.outcome.in_(["pending", "running"]),
    ).values(outcome="unfinished"))
    attempt = UsageApply(
        lifetime_id=lifetime.id, run_id=orm.tfcloud_run.run_id,
        commit_sha=orm.tfcloud_run.commit_sha, initiated_by=initiated_by,
        kind="update" if lifetime.healthy_at or lifetime.predates_tracking else "deployment",
    )
    db.session.add(attempt)
    db.session.commit()
    return attempt


def accepted(attempt):
    db.session.refresh(attempt)
    if attempt.applied_at is None and attempt.healthy_at is None:
        attempt.applied_at = utcnow()
        if attempt.outcome == "pending":
            attempt.outcome = "running"
        lifetime = db.session.get(UsageLifetime, attempt.lifetime_id)
        first_attempt = db.session.scalar(db.select(UsageApply.id).where(
            UsageApply.lifetime_id == lifetime.id,
        ).order_by(UsageApply.id).limit(1))
        if lifetime.started_at is None and not lifetime.predates_tracking and first_attempt == attempt.id:
            lifetime.started_at = attempt.applied_at
    db.session.commit()


def observe(orm):
    if not orm.tfcloud_run or not orm.tfcloud_run.run_id:
        return
    attempt = db.session.scalar(db.select(UsageApply).filter_by(run_id=orm.tfcloud_run.run_id))
    if attempt is None or attempt.outcome not in ("pending", "running", "failed"):
        return
    if orm.status == Status.PROVISIONING_SUCCESS:
        now = utcnow()
        changed = db.session.execute(db.update(UsageApply).where(
            UsageApply.id == attempt.id, UsageApply.outcome.in_(["pending", "running", "failed"]),
        ).values(healthy_at=now, outcome="successful"))
        if changed.rowcount != 1:
            return
        db.session.execute(db.update(UsageLifetime).where(
            UsageLifetime.id == attempt.lifetime_id, UsageLifetime.healthy_at.is_(None),
            UsageLifetime.predates_tracking.is_(False),
        ).values(healthy_at=now))
    elif orm.status in (Status.BUILD_ERROR, Status.PLAN_ERROR, Status.PROVISIONING_ERROR):
        db.session.execute(db.update(UsageApply).where(
            UsageApply.id == attempt.id, UsageApply.outcome.in_(["pending", "running"]),
        ).values(outcome="failed"))


def end_lifetime(orm):
    lifetime = current_lifetime(orm)
    if lifetime:
        lifetime.ended_at = utcnow()
        lifetime.active_cluster_id = None
        for attempt in db.session.scalars(db.select(UsageApply).where(
            UsageApply.lifetime_id == lifetime.id,
            UsageApply.outcome.in_(["pending", "running"]),
        )):
            attempt.outcome = "unfinished"
    orm.usage_legacy = False
