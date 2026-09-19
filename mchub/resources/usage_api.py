import datetime
import math
import statistics

from flask import request
from .api_view import ApiView
from ..database import db
from ..exceptions.invalid_usage_exception import InvalidUsageException
from ..models.usage import UsageApply, UsageLifetime, UsageState, utcnow
from ..services.usage import POLL_INTERVAL


def iso(value):
    return value.isoformat() + "Z" if value else None


def durations(values):
    values = sorted(values)
    return {
        "count": len(values),
        "average_seconds": statistics.mean(values) if values else None,
        "median_seconds": statistics.median(values) if values else None,
        "p95_seconds": values[math.ceil(len(values) * .95) - 1] if values else None,
    }


def adoption(lifetimes, first, start, end):
    successful = [row for row in lifetimes if row.healthy_at and start <= row.healthy_at < end]
    creators = {row.creator for row in successful if row.creator}
    newcomers = {creator for creator in creators if start <= first[creator] < end}
    return {
        "successful_deployments": len(successful),
        "distinct_clusters": len({row.cluster_id for row in successful}),
        "unique_creators": len(creators),
        "first_time_creators": len(newcomers),
        "returning_creators": len(creators - newcomers),
        "active_projects": len({row.project_id for row in successful}),
    }


class UsageAPI(ApiView):
    def get(self, user):
        if not getattr(user, "is_admin", False):
            raise InvalidUsageException("Only hub admins can view usage statistics.", status_code=403)
        now = utcnow()
        month_index = now.year * 12 + now.month - 1 - 11
        default_start = datetime.datetime(month_index // 12, month_index % 12 + 1, 1)
        try:
            start = datetime.datetime.combine(datetime.date.fromisoformat(request.args.get("start", default_start.date().isoformat())), datetime.time())
            end_date = datetime.date.fromisoformat(request.args.get("end", now.date().isoformat()))
            end = datetime.datetime.combine(end_date + datetime.timedelta(days=1), datetime.time())
            page = int(request.args.get("page", 1))
            if start >= end or (end - start).days > 3660 or page < 1:
                raise ValueError
        except (ValueError, OverflowError):
            raise InvalidUsageException("Use valid YYYY-MM-DD dates, a range of at most 10 years, and a positive page.")

        all_lifetimes = list(db.session.scalars(db.select(UsageLifetime).where(UsageLifetime.benchmark_run_id.is_(None))))
        first = {}
        for row in all_lifetimes:
            if row.healthy_at and row.creator:
                first[row.creator] = min(first.get(row.creator, row.healthy_at), row.healthy_at)
        projects = {row.project_id: row.project_name for row in all_lifetimes}
        project = request.args.get("project")
        lifetimes = [row for row in all_lifetimes if not project or row.project_id == project]
        lookup = {row.id: row for row in lifetimes}
        attempts = list(db.session.scalars(db.select(UsageApply).where(
            UsageApply.requested_at >= start, UsageApply.requested_at < end,
        ).order_by(UsageApply.requested_at.desc(), UsageApply.id.desc())))
        attempts = [row for row in attempts if row.lifetime_id in lookup]
        timing = [(row.healthy_at - row.applied_at).total_seconds() for row in attempts
                  if row.outcome == "successful" and row.applied_at and row.healthy_at]
        completed = [(row.ended_at - row.started_at).total_seconds() for row in lifetimes
                     if row.started_at and row.ended_at and start <= row.ended_at < end]
        ongoing = [(now - row.started_at).total_seconds() for row in lifetimes
                   if row.started_at and not row.ended_at]
        months = []
        cursor = start.replace(day=1)
        while cursor < end:
            following = end if cursor.year == 9999 and cursor.month == 12 else (
                cursor.replace(day=28) + datetime.timedelta(days=4)
            ).replace(day=1)
            months.append({"month": cursor.strftime("%Y-%m"), **adoption(lifetimes, first, max(start, cursor), min(end, following))})
            cursor = following
        state = db.session.get(UsageState, 1)
        rows = []
        for attempt in attempts[(page - 1) * 25:page * 25]:
            lifetime = lookup[attempt.lifetime_id]
            rows.append({
                "id": attempt.id, "hostname": lifetime.hostname,
                "project": lifetime.project_name, "creator": lifetime.creator,
                "initiated_by": attempt.initiated_by, "kind": attempt.kind,
                "run_id": attempt.run_id, "repository": lifetime.repository,
                "commit_sha": attempt.commit_sha, "outcome": attempt.outcome,
                "requested_at": iso(attempt.requested_at), "applied_at": iso(attempt.applied_at),
                "healthy_at": iso(attempt.healthy_at),
                "duration_seconds": (attempt.healthy_at - attempt.applied_at).total_seconds()
                    if attempt.healthy_at and attempt.applied_at else None,
            })
        return {
            "tracking_started_at": iso(state.tracking_started_at) if state else None,
            "last_poll_at": iso(state.last_poll_at) if state else None,
            "poll_interval_seconds": POLL_INTERVAL,
            "summary": adoption(lifetimes, first, start, end), "months": months,
            "projects": [{"id": key, "name": value} for key, value in sorted(projects.items(), key=lambda item: item[1])],
            "apply_to_healthy": durations(timing),
            "completed_lifetime": durations(completed), "ongoing_age": durations(ongoing),
            "failed_attempts": sum(row.outcome == "failed" for row in attempts),
            "unfinished_attempts": sum(row.outcome in ("pending", "running", "unfinished") for row in attempts),
            "legacy_lifetimes": sum(row.predates_tracking for row in lifetimes),
            "attempts": rows, "attempt_count": len(attempts), "page": page,
        }
