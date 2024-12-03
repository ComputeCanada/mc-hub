from threading import Thread, current_thread

from flask import request
from flask import current_app
from .api_view import ApiView
from ..exceptions.invalid_usage_exception import (
    ClusterNotFoundException,
    InvalidUsageException,
)
from ..models.cloud.project import Project
from ..models.magic_castle.cluster_status_code import ClusterStatusCode
from ..models.user import User
from ..models.magic_castle.magic_castle import MagicCastleORM, MagicCastle
from ..database import db


class MagicCastleAPI(ApiView):
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
            if orm and orm.project in user.projects:
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
            if not (orm and orm.project in user.projects):
                raise ClusterNotFoundException

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

            self._run_in_background(app, MagicCastle().plan_creation, json_data)
            return {}, 202

    def put(self, user: User, hostname):
        orm = db.session.execute(
            db.select(MagicCastleORM).filter_by(hostname=hostname)
        ).scalar_one_or_none()
        if not (orm and orm.project in user.projects):
            raise ClusterNotFoundException

        json_data = request.get_json()
        if not json_data:
            raise InvalidUsageException("No json data was provided")

        app = current_app._get_current_object()

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
        if not (orm and orm.project in user.projects):
            raise ClusterNotFoundException

        app = current_app._get_current_object()

        def destroy_cluster(hostname):
            orm = db.session.execute(
                db.select(MagicCastleORM).filter_by(hostname=hostname)
            ).scalar_one_or_none()
            if orm is None:
                raise ClusterNotFoundException
            MagicCastle(orm).plan_destruction()

        self._run_in_background(app, destroy_cluster, hostname, hostname=hostname)
        return {}, 202
