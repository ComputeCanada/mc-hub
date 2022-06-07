from flask import request
from sqlalchemy import inspect

from .api_view import ApiView
from ..database import db
from ..models.user import User
from ..models.cloud.project import Project, Provider, ENV_VALIDATORS
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
        try:
            provider = Provider(data["provider"])
            env = data["env"]
            name = data["name"]
        except KeyError as err:
            raise InvalidUsageException(f"Missing required field {err}")

        try:
            env = ENV_VALIDATORS[provider](env)
        except Exception as err:
            raise InvalidUsageException("Missing required environment variables")

        project = Project(name=name, provider=provider, env=env)
        user.orm.projects.append(project)
        db.session.add(project)
        if inspect(user.orm).identity is None:
            db.session.add(user.orm)
        db.session.commit()
        return {
            "id": project.id,
            "name": project.name,
            "provider": project.provider,
        }, 200

    def delete(self, user: User, id: int):
        project = Project.query.get(id)
        if project is None or project not in user.orm.projects:
            raise InvalidUsageException("Invalid project id")
        user.orm.projects.remove(project)
        db.session.delete(project)
        db.session.commit()
        return "", 200
