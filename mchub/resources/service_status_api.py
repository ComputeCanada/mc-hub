from .api_view import ApiView
from ..services.service_status import read_status


class ServiceStatusAPI(ApiView):
    def get(self, user):
        return read_status(), 200
