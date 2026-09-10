from decimal import Decimal, InvalidOperation

from flask import request

from .api_view import ApiView
from ..database import db
from ..models.user import User, UserORM
from ..services.terraform_cloud_api import get_terraform_cloud, TerraformCloudVariable
from ..services.github_api import get_github_storage
from ..models.cloud.project import Project, Provider, ENV_VALIDATORS
from ..models.cloud.aws_manager import AWSManager
from ..models.cloud.openstack_manager import OpenStackManager
from ..exceptions.invalid_usage_exception import (
    InvalidUsageException,
)
from ..exceptions.server_exception import (
    TerraformCloudException,
    GithubStorageException,
)


def parse_price(value, provider):
    if value is None or value == "":
        return None
    try:
        price = Decimal(str(value))
        if (provider != Provider.AWS or not price.is_finite() or price < 0
                or price >= Decimal("100000000") or price.as_tuple().exponent < -10):
            raise ValueError
        return price
    except (InvalidOperation, ValueError):
        raise InvalidUsageException("Maximum instance price must be a nonnegative USD/hour amount with at most 10 decimal places, for an AWS project.")


def aws_settings(project):
    if project.provider != Provider.AWS:
        return {}
    price = getattr(project, "max_instance_hourly_price", None)
    return {"region": project.env.get("AWS_DEFAULT_REGION"),
            "max_instance_hourly_price": str(price) if price is not None else None}


class ProjectAPI(ApiView):
    def get(self, user: User, id: int = None):
        if id is not None:
            project = db.session.get(Project, id)
            if project is None or project not in user.projects:
                raise InvalidUsageException("Invalid project id")
            is_admin = user.is_project_admin(project)
            return {
                "id": project.id,
                "name": project.name,
                "provider": project.provider,
                **aws_settings(project),
                "github_template": project.github_template,
                "nb_clusters": len(project.magic_castles),
                "admin": is_admin,
                "members": [member.scoped_id for member in project.members]
                if is_admin
                else [],
                "admins": [admin.scoped_id for admin in project.admins]
                if is_admin
                else [],
            }
        else:
            return [
                {
                    "id": project.id,
                    "name": project.name,
                    "provider": project.provider,
                    **aws_settings(project),
                    "github_template": project.github_template,
                    "nb_clusters": len(project.magic_castles),
                    "admin": user.is_project_admin(project),
                }
                for project in user.projects
            ]

    def post(self, user: User):
        if not getattr(user, "is_admin", False):
            raise InvalidUsageException(
                "Only admins can create projects", status_code=403
            )
        data = request.get_json()
        if not data:
            raise InvalidUsageException("No json data was provided")
        try:
            provider = Provider(data["provider"])
            env = data["env"]
            name = data["name"]
            github_template = data["github_template"]
        except KeyError as err:
            raise InvalidUsageException(f"Missing required field {err}")
        max_price = parse_price(data.get("max_instance_hourly_price"), provider)
        agent_pool_name = data.get("agent_pool_name")

        try:
            env = ENV_VALIDATORS[provider](env)
        except Exception as err:
            raise InvalidUsageException("Missing required environment variables")

        if provider == Provider.AWS:
            AWSManager(Project(provider=provider, env=env)).validate_project()

        if provider == Provider.OPENSTACK and env.get("OS_SUBNET_ID"):
            if env["OS_SUBNET_ID"] not in {
                subnet["id"] for subnet in OpenStackManager(Project(provider=provider, env=env)).subnets()
            }:
                raise InvalidUsageException("Select an available OpenStack subnet.")

        if github_template:
            try:
                get_github_storage().validate_template(github_template)
            except GithubStorageException as e:
                raise InvalidUsageException(str(e))

        try:
            tfcloud_project_id = get_terraform_cloud().create_project(
                name, agent_pool_name=agent_pool_name
            )
        except TerraformCloudException:
            raise InvalidUsageException(f"Error with Terraform Cloud project creation")

        terraform_vars = []
        for k, v in env.items():
            sensitive = "SECRET" in k or "TOKEN" in k
            terraform_vars.append(
                TerraformCloudVariable(name=k, value=v, sensitive=sensitive)
            )
        get_terraform_cloud().set_project_variable_set(
            tfcloud_project_id, name, terraform_vars
        )

        if user.orm.id is None:
            db.session.add(user.orm)
            db.session.commit()

        project = Project(
            name=name,
            provider=provider,
            env=env,
            github_template=github_template,
            tfcloud_project_id=tfcloud_project_id,
            max_instance_hourly_price=max_price,
        )
        project.admins.append(user.orm)
        db.session.add(project)
        db.session.commit()
        return {
            "id": project.id,
            "name": project.name,
            "provider": project.provider,
            **aws_settings(project),
            "github_template": project.github_template,
            "nb_clusters": len(project.magic_castles),
            "admin": True,
        }, 200

    def patch(self, user: User, id: int):
        project = db.session.get(Project, id)
        if project is None or project not in user.projects:
            raise InvalidUsageException("Invalid project id")
        if not user.is_project_admin(project):
            raise InvalidUsageException(
                "Cannot edit project membership that you are not the admin of"
            )
        data = request.get_json()
        if not data:
            raise InvalidUsageException("No json data was provided")

        max_price = parse_price(data.get("max_instance_hourly_price"), project.provider)

        # Validate before changing any external project settings.
        if "env" in data:
            try:
                env = ENV_VALIDATORS[project.provider]({**project.env, **data["env"]} if project.provider == Provider.AWS else data["env"])
            except Exception:
                raise InvalidUsageException("Missing required environment variables")
            if project.provider == Provider.OPENSTACK and project.env.get("OS_SUBNET_ID"):
                env["OS_SUBNET_ID"] = project.env["OS_SUBNET_ID"]
            if project.provider == Provider.AWS:
                if project.magic_castles and env["AWS_DEFAULT_REGION"] != project.env["AWS_DEFAULT_REGION"]:
                    raise InvalidUsageException("A project with clusters cannot change AWS region.")
                AWSManager(Project(provider=project.provider, env=env)).validate_project()

        if "github_template" in data:
            if data["github_template"]:
                try:
                    get_github_storage().validate_template(data["github_template"])
                except GithubStorageException as e:
                    raise InvalidUsageException(str(e))
            project.github_template = data["github_template"]

        if "agent_pool_name" in data:
            try:
                get_terraform_cloud().update_project(project.tfcloud_project_id, data["agent_pool_name"])
            except TerraformCloudException:
                raise InvalidUsageException("Error updating agent pool")

        if "env" in data:
            terraform_vars = [
                TerraformCloudVariable(name=k, value=v, sensitive="SECRET" in k or "TOKEN" in k)
                for k, v in env.items()
            ]
            get_terraform_cloud().replace_project_variable_set(
                project.tfcloud_project_id, project.name, terraform_vars
            )
            project.env = env

        if "max_instance_hourly_price" in data:
            project.max_instance_hourly_price = max_price

        add_members = data.get("add", [])
        del_members = data.get("del", [])
        add_admins = data.get("add_admins", [])
        del_admins = data.get("del_admins", [])

        default_domain = user.domain

        for username in add_members:
            if "@" not in username:
                username = f"{username}@{default_domain}"
            member = db.session.execute(
                db.select(UserORM).filter_by(scoped_id=username)
            ).scalar_one_or_none()
            if not member:
                member = UserORM(scoped_id=username)
                db.session.add(member)
            if project not in member.projects:
                member.projects.append(project)

        for username in del_members:
            if "@" not in username:
                username = f"{username}@{default_domain}"
            member = db.session.execute(
                db.select(UserORM).filter_by(scoped_id=username)
            ).scalar_one_or_none()
            if member and member.id != user.orm.id:
                if project in member.projects:
                    member.projects.remove(project)
                if member in project.admins:
                    project.admins.remove(member)

        for username in add_admins:
            if "@" not in username:
                username = f"{username}@{default_domain}"
            member = db.session.execute(
                db.select(UserORM).filter_by(scoped_id=username)
            ).scalar_one_or_none()
            if not member:
                member = UserORM(scoped_id=username)
                db.session.add(member)
            if project in member.projects:
                member.projects.remove(project)
            if member not in project.admins:
                project.admins.append(member)

        for username in del_admins:
            if "@" not in username:
                username = f"{username}@{default_domain}"
            member = db.session.execute(
                db.select(UserORM).filter_by(scoped_id=username)
            ).scalar_one_or_none()
            if member and member.id != user.orm.id and member in project.admins:
                project.admins.remove(member)
                if project not in member.projects:
                    member.projects.append(project)

        db.session.commit()
        return {}, 200

    def delete(self, user: User, id: int):
        project = db.session.get(Project, id)
        if project is None or project not in user.projects:
            raise InvalidUsageException("Invalid project id")
        if not user.is_project_admin(project):
            raise InvalidUsageException(
                "Cannot remove project that you are not the admin of"
            )
        if len(project.magic_castles) > 0:
            raise InvalidUsageException("Cannot remove project with running clusters")
        db.session.delete(project)
        db.session.commit()
        return {}, 200


class AWSRegionsAPI(ApiView):
    def post(self, user: User):
        data = request.get_json() or {}
        project = db.session.get(Project, data["project_id"]) if data.get("project_id") else None
        if data.get("project_id"):
            if project is None or project.provider != Provider.AWS or not user.is_project_admin(project):
                raise InvalidUsageException("Invalid project id", status_code=403)
        elif not getattr(user, "is_admin", False):
            raise InvalidUsageException("Only admins can discover AWS project regions", status_code=403)
        try:
            env = ENV_VALIDATORS[Provider.AWS]({**(project.env if project else {}), **data.get("env", {}), "AWS_DEFAULT_REGION": "us-east-1"})
        except Exception:
            raise InvalidUsageException("Provide AWS access credentials to load regions.")
        return {"regions": AWSManager(Project(provider=Provider.AWS, env=env)).regions()}


class OpenStackSubnetsAPI(ApiView):
    def post(self, user: User):
        if not getattr(user, "is_admin", False):
            raise InvalidUsageException("Only admins can discover OpenStack project subnets", status_code=403)
        data = request.get_json() or {}
        try:
            env = ENV_VALIDATORS[Provider.OPENSTACK](data.get("env", {}))
        except Exception:
            raise InvalidUsageException("Provide OpenStack credentials to load subnets.")
        return {"subnets": OpenStackManager(Project(provider=Provider.OPENSTACK, env=env)).subnets()}
