from ..resources.api_view import ApiView
from ..models.cloud.cloud_manager import CloudManager
from ..models.user import User
from ..models.cloud.project import Project


class AvailableResourcesApi(ApiView):
    def get(self, user: User, hostname, cloud_id):
        allocated_resources = {}
        if hostname:
            mc = user.query_magic_castles(hostname=hostname)[0]
            cloud_id = mc.cloud_id
            allocated_resources = mc.allocated_resources
        project = Project.query.get(cloud_id)
        if project is None or project not in user.projects:
            return {
                "quotas": {},
                "possible_resources": {},
                "resource_details": {},
            }
        cloud = CloudManager(project=project, **allocated_resources)
        return cloud.available_resources
