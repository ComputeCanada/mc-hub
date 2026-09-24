"""Forecast planned demand against project capacity."""
from collections import Counter
from datetime import datetime, timezone
import math
import re
from types import SimpleNamespace
import time

from ..database import db
from ..exceptions.invalid_usage_exception import InvalidUsageException
from ..models.capacity_plan import CapacityPlan
from ..models.cloud.cloud_manager import CloudManager
from ..models.magic_castle.magic_castle import MagicCastleORM
from ..models.magic_castle.cluster_status_code import ClusterStatusCode as Status


def parse_period(data):
    try:
        dates = [datetime.fromisoformat(data[key].replace("Z", "+00:00")) for key in ("starts_at", "ends_at")]
        if any(d.tzinfo is None for d in dates):
            raise ValueError
        start, end = [d.timestamp() for d in dates]
        if not (math.isfinite(start) and math.isfinite(end) and time.time() < start < end):
            raise ValueError
        return start, end
    except (KeyError, AttributeError, TypeError, ValueError, OverflowError):
        raise InvalidUsageException("Choose a future start and a later end, including a timezone.")


def iso(value):
    return datetime.fromtimestamp(value, timezone.utc).isoformat()


def gpu_count(instance_type):
    """Count allocated GPUs, including fractional AWS GPU partitions."""
    gpus = instance_type.get("gpus")
    if isinstance(gpus, (int, float)):
        return gpus
    if isinstance(gpus, list) and gpus:
        return sum((gpu.get("count") or 0) * (gpu.get("partition_size") or 1) for gpu in gpus)
    # OpenStack names encode GPU count in g<count>-... or a GPU model x<count> suffix.
    match = re.match(r"^g([0-9]+)(?:-[0-9.]+gb)?-", instance_type.get("name", ""))
    if not match:
        match = re.match(r"^gpu.*-[a-zA-Z][a-zA-Z0-9]*x([0-9]+)$", instance_type.get("name", ""))
    return int(match[1]) if match else 0


def gpu_demand(project, definition, manager):
    groups = definition.get("instances", {})
    if not groups:
        return 0
    types = (manager.types_by_name if project.provider == "aws" else
             {t["name"]: t for t in manager.resource_details["instance_types"]})
    return sum(group["count"] * gpu_count(types.get(group["type"], {"name": group["type"]}))
               for group in groups.values())


def resource_demand(project, definition, manager=None):
    manager = manager or CloudManager(project).manager
    if project.provider == "aws":
        demand, issues = manager.demand(definition)
        volumes, volume_issues = manager.volume_demand(definition)
        demand.update(volumes)
        issues += volume_issues + manager.zone_issues(definition)
        if issues:
            raise InvalidUsageException(" ".join(issue["message"] for issue in issues))
        demand["gpus"] = gpu_demand(project, definition, manager)
        return dict(demand)
    types = {t["name"]: t for t in manager.resource_details["instance_types"]}
    demand = Counter()
    groups = definition.get("instances")
    if not isinstance(groups, dict) or not groups:
        raise InvalidUsageException("Define at least one instance group.")
    for group in groups.values():
        if not isinstance(group, dict) or type(group.get("count")) is not int or group["count"] < 0:
            raise InvalidUsageException("Instance counts must be nonnegative integers.")
        count = group["count"]
        tags = group.get("tags", [])
        if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
            raise InvalidUsageException("Instance tags must be a list of strings.")
        flavor = types.get(group.get("type")) if isinstance(group.get("type"), str) else None
        if flavor is None:
            raise InvalidUsageException("Select an available instance type for every group.")
        demand["instance_count"] += count
        for key, field in (("ram", "ram"), ("vcpus", "vcpus"),
                           ("volume_count", "required_volume_count"), ("volume_size", "required_volume_size")):
            demand[key] += count * flavor.get(field, 0)
        if "disk_size" in group:
            size = group["disk_size"]
            if type(size) is not int or size <= 0:
                raise InvalidUsageException("Root disk sizes must be positive integers.")
            # Explicit root sizes may require boot volumes even when the flavor
            # includes local storage. Account conservatively for those volumes.
            demand["volume_count"] += count * (1 - flavor.get("required_volume_count", 0))
            demand["volume_size"] += count * max(0, size - flavor.get("required_volume_size", 0))
        demand["ips"] += count if "public" in tags else 0
    volumes = definition.get("volumes", {})
    if not isinstance(volumes, dict):
        raise InvalidUsageException("Volumes must be grouped by instance tag.")
    for tag, entries in volumes.items():
        if not isinstance(entries, dict):
            raise InvalidUsageException("Invalid volume group.")
        count = sum(g["count"] for g in groups.values() if tag in g.get("tags", []))
        for volume in entries.values():
            size = volume.get("size") if isinstance(volume, dict) else None
            if type(size) not in (int, float) or not math.isfinite(size) or size <= 0:
                raise InvalidUsageException("Volume sizes must be positive numbers.")
            demand["volume_count"] += count
            demand["volume_size"] += count * size
    demand["gpus"] = gpu_demand(project, definition, manager)
    return dict(demand)


def budget(project, manager):
    if project.provider == "aws":
        return dict(manager.budget)
    return {key: None if manager.total_quotas[key]["max"] is None else quota["max"]
            for key, quota in manager.quotas.items()}


def planning_budget(project, manager):
    if project.provider == "openstack":
        return {key: quota["max"] for key, quota in manager.total_quotas.items()}
    return budget(project, manager)


def segments(plans, available, start, end):
    """Half-open intervals avoid conflicts between back-to-back plans."""
    if end <= start:
        return []
    plans = [p for p in plans if p.starts_at < end and start < p.ends_at]
    points = sorted({start, end} | {max(start, p.starts_at) for p in plans} | {min(end, p.ends_at) for p in plans})
    result = []
    for left, right in zip(points, points[1:]):
        demand = Counter()
        active = [p for p in plans if p.starts_at <= left < p.ends_at]
        for plan in active:
            demand.update(plan.demand)
        shortages = {key: value - available[key] for key, value in demand.items()
                     if available.get(key) is not None and value > available[key]}
        result.append({"starts_at": iso(left), "ends_at": iso(right), "demand": dict(demand),
                       "shortages": shortages, "plan_ids": [p.id for p in active]})
    return result


def forecast(project, start, end, candidate=None, exclude_plan_id=None):
    manager = CloudManager(project).manager
    available = planning_budget(project, manager)
    plans = list(db.session.scalars(db.select(CapacityPlan).where(
        CapacityPlan.project_id == project.id, CapacityPlan.status != "cancelled",
        CapacityPlan.starts_at < end, CapacityPlan.ends_at > start)))
    plans = [p for p in plans if p.id != exclude_plan_id]
    # Older plans predate GPU snapshots; derive their counts without modifying the DB.
    gpu_counts = {p.id: p.demand.get("gpus") if "gpus" in p.demand else gpu_demand(project, p.definition, manager)
                  for p in plans}
    plans = [SimpleNamespace(id=p.id, starts_at=p.starts_at, ends_at=p.ends_at,
                             cluster_usage_id=p.cluster_usage_id,
                             demand={**p.demand, "gpus": gpu_counts[p.id]}) for p in plans]
    if project.provider != "openstack":
        # Once deployed, cloud inventory already includes this plan. Keep in-flight
        # plans until deployed, accepting temporary conservative double counting.
        deployed = set(db.session.scalars(db.select(MagicCastleORM.usage_id).where(MagicCastleORM.undeployed.is_(False),
            MagicCastleORM.status.in_([Status.PROVISIONING_RUNNING, Status.PROVISIONING_SUCCESS, Status.PROVISIONING_ERROR]))))
        for plan in plans:
            if plan.cluster_usage_id in deployed:
                # GPU reporting has no inventory baseline or quota: keep counting
                # the allocation through the declared period after deployment.
                plan.demand = {"gpus": plan.demand["gpus"]}
    if candidate:
        plans.append(candidate)
    return {"quota_basis": "project_total" if project.provider == "openstack" else "currently_available",
            "plan_gpu_counts": gpu_counts,
            "available": available, "segments": segments(plans, available, start, end),
            "checked_at": iso(time.time()),
            "assumption": (
                "Planned usage is compared with the full OpenStack project quotas. Current unplanned usage is not deducted."
                if project.provider == "openstack" else
                "Current cloud usage is held constant. Plans add demand during their periods."
            ) + " This is an estimate, not a cloud reservation; quota does not guarantee physical capacity."}


def validate_plan_apply(orm):
    """An un-applied manual plan must not launch after its cleanup deadline."""
    plan = db.session.scalar(db.select(CapacityPlan).where(CapacityPlan.cluster_usage_id == orm.usage_id))
    if plan is not None and plan.ends_at <= time.time():
        from .terraform_cloud_api import get_terraform_cloud
        _, is_destroy = get_terraform_cloud().get_run_status(orm.tfcloud_run.run_id)
        if not is_destroy:
            raise InvalidUsageException("This capacity period has ended. Create a new capacity plan before deploying.")
