from .api_view import ApiView
from ..models.template import DEFAULT
from ..models.user import User


class TemplateAPI(ApiView):
    def get(self, user: User, template_name):
        return DEFAULT
