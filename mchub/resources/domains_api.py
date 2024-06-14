from ..resources.api_view import APIView
from ..models.cloud.dns_manager import DnsManager
from ..models.user import User

class DomainsAPI(APIView):
    def get(self, user: User):
        return {
            "domains": DnsManager.get_available_domains(),
        }