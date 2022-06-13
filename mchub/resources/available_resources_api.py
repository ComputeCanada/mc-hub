from ..resources.api_view import ApiView
from ..models.cloud.cloud_manager import CloudManager
from ..models.user import User
from ..models.cloud.project import Project
from ..models.magic_castle.magic_castle import MagicCastleORM, MagicCastle
from ..exceptions.invalid_usage_exception import (
    ClusterNotFoundException,
)


class AvailableResourcesApi(ApiView):
    def get(self, user: User, hostname, cloud_id):
        if hostname:
            orm = MagicCastleORM.query.filter_by(hostname=hostname).first()
            if orm and orm.project in user.projects:
                mc = MagicCastle(orm)
            else:
                raise ClusterNotFoundException
            project = mc.project
            allocated_resources = mc.allocated_resources
        elif cloud_id:
            project = Project.query.get(cloud_id)
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
