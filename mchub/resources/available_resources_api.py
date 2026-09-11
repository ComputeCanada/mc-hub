from ..resources.api_view import ApiView
from ..models.cloud.cloud_manager import CloudManager
from ..models.user import User
from ..models.cloud.project import Project
from ..models.magic_castle.magic_castle import MagicCastleORM, MagicCastle
from ..exceptions.invalid_usage_exception import (
    ClusterNotFoundException,
)
from ..database import db
from flask import request
from ..exceptions.invalid_usage_exception import InvalidUsageException, BusyClusterException


class AvailableResourcesApi(ApiView):
    def get(self, user: User, hostname, cloud_id):
        if hostname:
            orm = db.session.execute(
                db.select(MagicCastleORM).filter_by(hostname=hostname)
            ).scalar_one_or_none()
            if orm and orm.project in user.projects and user.can_access_cluster(orm):
                mc = MagicCastle(orm)
            else:
                raise ClusterNotFoundException
            project = mc.project
            allocated_resources = mc.allocated_resources
        elif cloud_id:
            project = db.session.get(Project, cloud_id)
            if project is None or project not in user.projects:
                return {
                    "quotas": {},
                    "possible_resources": {},
                    "resource_details": {},
                }
            allocated_resources = {}
        else:
            return {
                "quotas": {},
                "possible_resources": {},
                "resource_details": {},
            }
        cloud = CloudManager(project=project, **allocated_resources)
        return cloud.available_resources

    def post(self, user: User, hostname, cloud_id):
        resource_ids = {}
        if hostname:
            orm = db.session.scalar(db.select(MagicCastleORM).filter_by(hostname=hostname))
            if not (orm and orm.project in user.projects and user.can_access_cluster(orm)):
                raise ClusterNotFoundException
            mc = MagicCastle(orm)
            if mc.is_busy:
                raise BusyClusterException
            project = orm.project
            if project.provider == "aws":
                resource_ids = mc.aws_resource_ids
        else:
            project = db.session.get(Project, cloud_id)
            if project is None or project not in user.projects:
                raise InvalidUsageException("Invalid project id", status_code=403)
        if project.provider != "aws":
            raise InvalidUsageException("Feasibility checks are available for AWS projects only.")
        definition = request.get_json()
        if not isinstance(definition, dict):
            raise InvalidUsageException("Provide a cluster definition.")
        manager = CloudManager(project, resource_ids=resource_ids).manager
        return manager.editor_resources(definition)
