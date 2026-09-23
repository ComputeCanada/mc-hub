import time
from copy import deepcopy

from flask import request
from marshmallow import ValidationError

from .api_view import ApiView
from ..database import db
from ..exceptions.invalid_usage_exception import InvalidUsageException
from ..models.capacity_plan import CapacityPlan
from ..models.cloud.project import Project
from ..models.magic_castle.magic_castle import MagicCastle
from ..models.magic_castle.magic_castle_configuration import MagicCastleConfiguration
from ..services.capacity import parse_period, iso, resource_demand, forecast


def authorize(user, project_id):
    project = db.session.get(Project, project_id)
    if project is None or project not in user.projects:
        raise InvalidUsageException("Invalid project id", status_code=403)
    return project


def can_manage(user, plan):
    return hasattr(user, "orm") and (user.orm.id == plan.owner_id or user.is_project_admin(plan.project))


def serialize(plan, user, detail=False):
    result = {"id": plan.id, "owner": plan.owner.scoped_id,
              "starts_at": iso(plan.starts_at), "ends_at": iso(plan.ends_at),
              "name": plan.definition["cluster_name"], "demand": plan.demand,
              "auto_create": plan.auto_create, "status": plan.status,
              "message": plan.message, "can_manage": can_manage(user, plan),
              "can_cancel": can_manage(user, plan) and plan.cluster_usage_id is None and plan.status in {"planned", "failed"}}
    if detail and can_manage(user, plan):
        result["definition"] = plan.definition
    if can_manage(user, plan) and plan.cluster_usage_id:
        from ..models.magic_castle.magic_castle import MagicCastleORM
        cluster = db.session.scalar(db.select(MagicCastleORM).where(MagicCastleORM.usage_id == plan.cluster_usage_id))
        if cluster is not None:
            result["hostname"] = cluster.hostname
    return result


class CapacityAPI(ApiView):
    def get(self, user, project_id, plan_id=None):
        project = authorize(user, project_id)
        if plan_id is not None:
            plan = db.session.get(CapacityPlan, plan_id)
            if plan is None or plan.project_id != project_id or not can_manage(user, plan):
                raise InvalidUsageException("Invalid capacity plan", status_code=403)
            return serialize(plan, user, detail=True)
        now = time.time()
        plans = list(db.session.scalars(db.select(CapacityPlan).where(
            CapacityPlan.project_id == project_id,
            ((CapacityPlan.ends_at > now) | CapacityPlan.status.in_(["starting", "manual_starting", "ending", "cleanup_pending", "cleanup_failed", "failed"])),
            CapacityPlan.status != "cancelled").order_by(CapacityPlan.starts_at)))
        end = max([p.ends_at for p in plans] + [now + 30 * 86400])
        result = {"plans": [serialize(p, user) for p in plans]}
        try:
            result["forecast"] = forecast(project, now, end)
            gpu_counts = result["forecast"].pop("plan_gpu_counts", {})
            for item in result["plans"]:
                if item["id"] in gpu_counts:
                    item["demand"] = {**item["demand"], "gpus": gpu_counts[item["id"]]}
        except Exception:
            # Plans remain accessible when cloud discovery is unavailable.
            result["forecast"] = None
            result["warning"] = "Unable to check cloud quota. Availability is unknown; retry later."
        return result

    def post(self, user, project_id, plan_id=None, preview=False):
        project = authorize(user, project_id)
        if not hasattr(user, "orm"):
            raise InvalidUsageException("Capacity planning requires a user identity", status_code=403)
        data = request.get_json()
        if not isinstance(data, dict) or not isinstance(data.get("definition"), dict):
            raise InvalidUsageException("Provide a cluster definition and a period.")
        start, end = parse_period(data)
        if type(data.get("auto_create", False)) is not bool:
            raise InvalidUsageException("Automatic creation must be a boolean.")
        definition = deepcopy(data["definition"])
        definition["cloud"] = {"id": project.id}
        definition["expiration_date"] = None
        try:
            MagicCastleConfiguration(project.provider, definition)
        except (ValidationError, TypeError, ValueError):
            raise InvalidUsageException("Invalid cluster configuration.")
        MagicCastle.validate_creation_version(definition)
        plan = CapacityPlan(project_id=project.id, owner_id=user.orm.id,
                            definition=definition, starts_at=start, ends_at=end,
                            auto_create=data.get("auto_create", False), status="planned",
                            demand=resource_demand(project, definition))
        report = forecast(project, start, end, candidate=plan)
        if preview:
            return report
        db.session.add(plan)
        db.session.commit()
        return {"plan": serialize(plan, user), "forecast": report}, 201

    def delete(self, user, project_id, plan_id):
        authorize(user, project_id)
        plan = db.session.get(CapacityPlan, plan_id)
        if plan is None or plan.project_id != project_id or not can_manage(user, plan):
            raise InvalidUsageException("Invalid capacity plan", status_code=403)
        result = db.session.execute(db.update(CapacityPlan).where(
            CapacityPlan.id == plan.id, CapacityPlan.cluster_usage_id.is_(None), CapacityPlan.status.in_(["planned", "failed"])
        ).values(status="cancelled"))
        if result.rowcount != 1:
            db.session.rollback()
            raise InvalidUsageException("A plan that has started cannot be cancelled.", status_code=409)
        db.session.commit()
        return {}, 200
