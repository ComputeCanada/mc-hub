from .api_view import APIView
from ..models.template import DEFAULT
from ..models.user import User


class TemplateAPI(APIView):
    def get(self, user: User, template_name):
        return DEFAULT
