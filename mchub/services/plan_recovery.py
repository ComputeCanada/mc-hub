"""Recover planning intent without depending on the initiating HTTP worker."""
import hashlib
import json
import logging
import secrets
from datetime import datetime, timedelta, timezone

from ..database import db
from ..models.terraform_cloud import TerraformCloudRunORM as Run

logger = logging.getLogger(__name__)


class PlanOwnershipLost(Exception):
    """The worker must stop without changing a replacement owner's status."""


def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def fingerprint(variables):
    return hashlib.sha256(json.dumps(variables, sort_keys=True).encode()).hexdigest()


def legacy_variables(variables):
    """Ignore only the generated proxy token's randomized encryption envelope.

    All user settings, including user-provided encrypted hieradata, and the
    generated workspace/proxy URL must still match exactly.
    """
    variables = dict(variables)
    lines = variables.get("hieradata", "").splitlines()
    if (len(lines) >= 3
            and lines[-3].startswith("profile::slurm::controller::tfe_token: ")
            and lines[-2].startswith("profile::slurm::controller::tfe_workspace: ")
            and lines[-1].startswith("profile::slurm::controller::tfe_proxy_url: ")):
        lines[-3] = "profile::slurm::controller::tfe_token: <generated>"
        variables["hieradata"] = "\n".join(lines)
    return variables


def acquire(run, seconds=360):
    owner = secrets.token_hex(16)
    result = db.session.execute(db.update(Run).where(
        Run.id == run.id,
        db.or_(Run.lease_until.is_(None), Run.lease_until < now()),
    ).values(lease_owner=owner, lease_until=now() + timedelta(seconds=seconds)))
    db.session.commit()
    return owner if result.rowcount == 1 else None


def start(run):
    """Publish a new intent and its owner atomically, before observers see it."""
    owner = secrets.token_hex(16)
    run.lease_owner = owner
    run.lease_until = now() + timedelta(seconds=360)
    db.session.commit()
    return owner


def renew(run_id, owner, seconds=360):
    result = db.session.execute(db.update(Run).where(
        Run.id == run_id, Run.lease_owner == owner, Run.lease_until >= now(),
    ).values(lease_until=now() + timedelta(seconds=seconds)))
    db.session.commit()
    return result.rowcount == 1


def release(run_id, owner):
    db.session.execute(db.update(Run).where(Run.id == run_id, Run.lease_owner == owner)
                       .values(lease_owner=None, lease_until=None))
    db.session.commit()


def recover(cluster):
    from ..models.magic_castle.cluster_status_code import ClusterStatusCode as Status
    from .github_api import get_github_storage
    from .terraform_cloud_api import get_terraform_cloud

    orm, run = cluster.orm, cluster.tfcloud_run
    if (orm.status not in {Status.BACKGROUND_TASK_RUNNING, Status.PLAN_RUNNING, Status.PLAN_ERROR}
            or not orm.tfcloud_workspace or run is None or run.plan is not None
            or orm.benchmark_id or orm.benchmark_run_id):
        return
    # Existing runs need recovery only when a recorded intent still owns queue
    # reconciliation. Ordinary status observation handles all other runs.
    if run.run_id and not run.intent_hash:
        return
    if not run.commit_sha and not run.intent_hash and orm.status != Status.BACKGROUND_TASK_RUNNING:
        return
    owner = acquire(run)
    if owner is None:
        return
    run_pk = run.id
    try:
        storage, tf = get_github_storage(), get_terraform_cloud()
        if not run.commit_sha:
            saved = storage.get_plan_configuration(cluster.hostname, require_tag=not bool(run.intent_hash))
            if saved is None:
                return
            sha, variables = saved
            matches = (fingerprint(variables) == run.intent_hash if run.intent_hash else
                       legacy_variables(variables) == legacy_variables(cluster._get_var_tf()))
            if not matches:
                logger.warning("Plan recovery configuration mismatch for %s", cluster.hostname)
                return
            if not renew(run_pk, owner):
                return
            run.commit_sha = sha
            run.intent_hash = fingerprint(variables)
            db.session.commit()
        if not run.run_id:
            if not run.intent_hash:
                run.intent_hash = "commit"
                db.session.commit()
            # A crash between saving the commit and creating its tag is safe to
            # retry: trigger_run verifies or creates that exact immutable tag.
            storage.trigger_run(cluster.hostname, run.commit_sha)
            run_id = tf.find_recovery_run(orm.tfcloud_workspace, run.commit_sha)
            if run_id is None or not renew(run_pk, owner):
                return
            run.run_id = run_id
            db.session.commit()
        if not renew(run_pk, owner):
            return
        tf.unblock_recovery_run(orm.tfcloud_workspace, run.run_id)
        if not renew(run_pk, owner):
            return
        run.intent_hash = None
        orm.status = Status.PLAN_RUNNING
        db.session.commit()
        logger.info("Recovered Terraform run %s for %s", run.run_id, cluster.hostname)
    except Exception:
        db.session.rollback()
        # External errors leave the intent intact for the next observer sweep.
        logger.warning("Plan recovery deferred for %s", cluster.hostname, exc_info=True)
    finally:
        release(run_pk, owner)
