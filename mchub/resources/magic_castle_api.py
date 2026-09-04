from threading import Thread, current_thread

from flask import request
from flask import current_app
from .api_view import ApiView
from ..exceptions.invalid_usage_exception import (
    BusyClusterException,
    ClusterNotFoundException,
    InvalidUsageException,
    PlanNotCreatedException,
    PlanNotReadyException,
    RunIDNotSet,
)
from ..models.cloud.project import Project
from ..models.magic_castle.cluster_status_code import ClusterStatusCode
from ..models.user import User
from ..models.magic_castle.magic_castle import MagicCastleORM, MagicCastle
from ..database import db


class MagicCastleAPI(ApiView):
    @staticmethod
    def _claim_background_task(orm):
        if (
            orm.status == ClusterStatusCode.BACKGROUND_TASK_RUNNING
            or MagicCastle(orm).is_busy
        ):
            raise BusyClusterException

        previous_status = orm.status
        result = db.session.execute(
            db.update(MagicCastleORM)
            .where(MagicCastleORM.id == orm.id)
            .where(MagicCastleORM.status == previous_status)
            .values(status=ClusterStatusCode.BACKGROUND_TASK_RUNNING)
            .execution_options(synchronize_session=False)
        )
        if result.rowcount != 1:
            db.session.rollback()
            raise BusyClusterException
        db.session.commit()

    @staticmethod
    def _run_in_background(app, target, *args, hostname=None):
        def worker():
            task_name = getattr(target, "__name__", "background_task")
            thread_name = current_thread().name
            app.logger.info(
                "Background task start: task=%s hostname=%s thread_name=%s",
                task_name,
                hostname,
                thread_name,
            )
            with app.app_context():
                try:
                    if hostname is not None:
                        orm = db.session.execute(
                            db.select(MagicCastleORM).filter_by(hostname=hostname)
                        ).scalar_one_or_none()
                        if orm is not None:
                            orm.status = ClusterStatusCode.BACKGROUND_TASK_RUNNING
                            db.session.commit()
                    target(*args)
                except Exception:
                    db.session.rollback()
                    app.logger.exception(
                        "Background task error: task=%s hostname=%s thread_name=%s",
                        task_name,
                        hostname,
                        thread_name,
                    )
                finally:
                    if hostname is not None:
                        orm = db.session.execute(
                            db.select(MagicCastleORM).filter_by(hostname=hostname)
                        ).scalar_one_or_none()
                        if (
                            orm is not None
                            and orm.status == ClusterStatusCode.BACKGROUND_TASK_RUNNING
                        ):
                            orm.status = ClusterStatusCode.PLAN_RUNNING
                            db.session.commit()
                    db.session.remove()
                    app.logger.info(
                        "Background task stop: task=%s hostname=%s thread_name=%s",
                        task_name,
                        hostname,
                        thread_name,
                    )

        thread = Thread(target=worker, daemon=True)
        thread.start()

    def get(self, user: User, hostname):
        if hostname:
            orm = db.session.execute(
                db.select(MagicCastleORM).filter_by(hostname=hostname)
            ).scalar_one_or_none()
            if orm and orm.project in user.projects and user.can_access_cluster(orm):
                return MagicCastle(orm).state
            else:
                raise ClusterNotFoundException
        else:
            return [mc.state for mc in user.magic_castles]

    def post(self, user: User, hostname, apply=False):
        app = current_app._get_current_object()
        if apply:
            orm = db.session.execute(
                db.select(MagicCastleORM).filter_by(hostname=hostname)
            ).scalar_one_or_none()
            if not (orm and orm.project in user.projects and user.can_access_cluster(orm)):
                raise ClusterNotFoundException

            magic_castle = MagicCastle(orm)
            if (
                orm.status == ClusterStatusCode.BACKGROUND_TASK_RUNNING
                or magic_castle.is_busy
            ):
                raise BusyClusterException
            if orm.status != ClusterStatusCode.CREATED:
                raise PlanNotReadyException
            if magic_castle.plan is None:
                raise PlanNotCreatedException
            if magic_castle.tfcloud_run.run_id is None:
                raise RunIDNotSet
            self._claim_background_task(orm)

            def apply_cluster(hostname):
                orm = db.session.execute(
                    db.select(MagicCastleORM).filter_by(hostname=hostname)
                ).scalar_one_or_none()
                if orm is None:
                    raise ClusterNotFoundException
                MagicCastle(orm).apply()

            self._run_in_background(app, apply_cluster, hostname, hostname=hostname)
            return {}, 202
        else:
            json_data = request.get_json()
            if not json_data:
                raise InvalidUsageException("No json data was provided")

            cloud = json_data.get("cloud", {"id": None})
            project = db.session.get(Project, cloud["id"])
            if project and project not in user.projects:
                raise InvalidUsageException("Invalid project id")
            MagicCastle.validate_creation_version(json_data)

            user_id = user.orm.id
            self._run_in_background(app, MagicCastle().plan_creation, json_data, user_id)
            return {}, 202

    def put(self, user: User, hostname):
        orm = db.session.execute(
            db.select(MagicCastleORM).filter_by(hostname=hostname)
        ).scalar_one_or_none()
        if not (orm and orm.project in user.projects and user.can_access_cluster(orm)):
            raise ClusterNotFoundException

        json_data = request.get_json()
        if not json_data:
            raise InvalidUsageException("No json data was provided")

        MagicCastle(orm).validate_version_unchanged(json_data)
        app = current_app._get_current_object()
        self._claim_background_task(orm)

        def modify_cluster(hostname, payload):
            orm = db.session.execute(
                db.select(MagicCastleORM).filter_by(hostname=hostname)
            ).scalar_one_or_none()
            if orm is None:
                raise ClusterNotFoundException
            MagicCastle(orm).plan_modification(payload)

        self._run_in_background(
            app, modify_cluster, hostname, json_data, hostname=hostname
        )
        return {}, 202

    def delete(self, user: User, hostname):
        orm = db.session.execute(
            db.select(MagicCastleORM).filter_by(hostname=hostname)
        ).scalar_one_or_none()
        if not (orm and orm.project in user.projects and user.can_access_cluster(orm)):
            raise ClusterNotFoundException

        app = current_app._get_current_object()

        def destroy_cluster(hostname):
            orm = db.session.execute(
                db.select(MagicCastleORM).filter_by(hostname=hostname)
            ).scalar_one_or_none()
            if orm is None:
                raise ClusterNotFoundException
            MagicCastle(orm).plan_destruction()

        # Make the planning transition visible before returning 202. Callers that
        # wait for CREATED can then be sure they are observing the destroy plan,
        # rather than a previously-created plan.
        self._claim_background_task(orm)
        self._run_in_background(app, destroy_cluster, hostname, hostname=hostname)
        return {}, 202
