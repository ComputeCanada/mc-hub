from flask import request
from sqlalchemy import inspect

from .api_view import ApiView
from ..database import db
from ..models.user import User
from ..models.cloud.project import Project, Provider
from ..exceptions.invalid_usage_exception import (
    InvalidUsageException,
)


class ProjectAPI(ApiView):
    def get(self, user: User):
        return user.projects

    def post(self, user: User):
        data = request.get_json()
        if not data:
            raise InvalidUsageException("No json data was provided")
        project = Project(
            name=data["name"], provider=Provider(data["provider"]), env=data["env"]
        )
        user.orm.projects.append(project)
        db.session.add(project)
        if inspect(user.orm).identity is None:
            db.session.add(user.orm)
        db.session.commit()
        return "", 200

    def delete(self, user: User, id: int):
        pass
