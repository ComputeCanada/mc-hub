from types import SimpleNamespace

import pytest
from flask import Flask

from mchub.exceptions.invalid_usage_exception import InvalidUsageException, ClusterNotFoundException
from mchub.models.cloud.project import Provider
from mchub.resources.project_api import ProjectAPI, AWSRegionsAPI
from mchub.resources.available_resources_api import AvailableResourcesApi
from mchub.resources.magic_castle_api import MagicCastleAPI


ENV = {"AWS_ACCESS_KEY_ID": "test", "AWS_SECRET_ACCESS_KEY": "secret", "AWS_DEFAULT_REGION": "ca-central-1"}


@pytest.fixture
def context():
    return Flask(__name__)


@pytest.fixture
def project():
    return SimpleNamespace(id=1, provider=Provider.AWS, env=ENV.copy(), magic_castles=[])


def test_region_change_with_clusters_is_rejected_before_external_mutation(context, project, mocker):
    project.magic_castles = [object()]
    database = mocker.patch("mchub.resources.project_api.db")
    database.session.get.return_value = project
    tf = mocker.patch("mchub.resources.project_api.get_terraform_cloud")
    user = SimpleNamespace(projects=[project], is_project_admin=lambda p: True)
    with context.test_request_context(json={"env": {"AWS_DEFAULT_REGION": "us-east-1"}, "agent_pool_name": "new"}):
        with pytest.raises(InvalidUsageException, match="cannot change AWS region"):
            ProjectAPI().patch(user, 1)
    tf.assert_not_called()


def test_invalid_rotated_credentials_rejected_before_mutation(context, project, mocker):
    database = mocker.patch("mchub.resources.project_api.db")
    database.session.get.return_value = project
    validate = mocker.patch("mchub.resources.project_api.AWSManager.validate_project", side_effect=InvalidUsageException("Denied"))
    tf = mocker.patch("mchub.resources.project_api.get_terraform_cloud")
    user = SimpleNamespace(projects=[project], is_project_admin=lambda p: True)
    with context.test_request_context(json={"env": {"AWS_SECRET_ACCESS_KEY": "invalid"}, "agent_pool_name": "new"}):
        with pytest.raises(InvalidUsageException, match="Denied"):
            ProjectAPI().patch(user, 1)
    validate.assert_called_once()
    assert project.env == ENV
    tf.assert_not_called()


def test_region_and_sensitive_token_are_synchronized_after_validation(context, project, mocker):
    project.name = "AWS project"
    project.tfcloud_project_id = "project-aws"
    database = mocker.patch("mchub.resources.project_api.db")
    database.session.get.return_value = project
    validate = mocker.patch("mchub.resources.project_api.AWSManager.validate_project")
    terraform = mocker.patch("mchub.resources.project_api.get_terraform_cloud").return_value
    user = SimpleNamespace(projects=[project], is_project_admin=lambda p: True, domain="example.org")
    with context.test_request_context(json={"env": {"AWS_DEFAULT_REGION": "us-east-1", "AWS_SESSION_TOKEN": "token"}}):
        assert ProjectAPI().patch(user, 1) == ({}, 200)
    validate.assert_called_once()
    variables = terraform.replace_project_variable_set.call_args.args[2]
    variables = {v.name: v for v in variables}
    assert variables["AWS_DEFAULT_REGION"].value == "us-east-1"
    assert variables["AWS_SECRET_ACCESS_KEY"].sensitive
    assert variables["AWS_SESSION_TOKEN"].sensitive
    assert project.env["AWS_DEFAULT_REGION"] == "us-east-1"


def test_region_discovery_requires_admin(context, mocker):
    manager = mocker.patch("mchub.resources.project_api.AWSManager")
    with context.test_request_context(json={"env": ENV}):
        with pytest.raises(InvalidUsageException) as error:
            AWSRegionsAPI().post(SimpleNamespace(is_admin=False))
    assert error.value.status_code == 403
    manager.assert_not_called()


def test_project_admin_can_load_regions_with_saved_credentials(context, project, mocker):
    database = mocker.patch("mchub.resources.project_api.db")
    database.session.get.return_value = project
    manager = mocker.patch("mchub.resources.project_api.AWSManager")
    manager.return_value.regions.return_value = ["ca-central-1"]
    with context.test_request_context(json={"project_id": 1}):
        result = AWSRegionsAPI().post(SimpleNamespace(is_admin=False, is_project_admin=lambda p: True))
    assert result == {"regions": ["ca-central-1"]}
    assert manager.call_args.args[0].env["AWS_SECRET_ACCESS_KEY"] == "secret"


def test_feasibility_requires_project_membership(context, project, mocker):
    database = mocker.patch("mchub.resources.available_resources_api.db")
    database.session.get.return_value = project
    cloud = mocker.patch("mchub.resources.available_resources_api.CloudManager")
    with context.test_request_context(json={}):
        with pytest.raises(InvalidUsageException):
            AvailableResourcesApi().post(SimpleNamespace(projects=[]), None, 1)
    cloud.assert_not_called()


def test_host_feasibility_requires_cluster_access(context, project, mocker):
    database = mocker.patch("mchub.resources.available_resources_api.db")
    database.session.scalar.return_value = SimpleNamespace(project=project)
    cloud = mocker.patch("mchub.resources.available_resources_api.CloudManager")
    user = SimpleNamespace(projects=[project], can_access_cluster=lambda c: False)
    with context.test_request_context(json={}):
        with pytest.raises(ClusterNotFoundException):
            AvailableResourcesApi().post(user, "other.example.org", None)
    cloud.assert_not_called()


def test_client_cannot_supply_edit_credits(context, project, mocker):
    database = mocker.patch("mchub.resources.available_resources_api.db")
    database.session.get.return_value = project
    cloud = mocker.patch("mchub.resources.available_resources_api.CloudManager")
    payload = {"instances": {}, "resource_ids": {"instances": ["i-forged"]}}
    with context.test_request_context(json=payload):
        AvailableResourcesApi().post(SimpleNamespace(projects=[project]), None, 1)
    cloud.assert_called_once_with(project, resource_ids={})


def test_direct_creation_is_blocked_before_background_work(context, project, mocker):
    database = mocker.patch("mchub.resources.magic_castle_api.db")
    database.session.get.return_value = project
    mocker.patch("mchub.resources.magic_castle_api.MagicCastle.validate_creation_version")
    verify = mocker.patch("mchub.resources.magic_castle_api.ensure_aws_feasible", side_effect=InvalidUsageException("Insufficient quota", 422))
    background = mocker.patch.object(MagicCastleAPI, "_run_in_background")
    payload = {"cloud": {"id": 1}, "instances": {}}
    with context.test_request_context(json=payload):
        with pytest.raises(InvalidUsageException, match="Insufficient quota"):
            MagicCastleAPI().post(SimpleNamespace(projects=[project]), None)
    verify.assert_called_once_with(project, payload)
    background.assert_not_called()


def test_modification_cannot_switch_project_to_bypass_quotas(context, project, mocker):
    database = mocker.patch("mchub.resources.magic_castle_api.db")
    database.session.execute.return_value.scalar_one_or_none.return_value = SimpleNamespace(project=project)
    background = mocker.patch.object(MagicCastleAPI, "_run_in_background")
    user = SimpleNamespace(projects=[project], can_access_cluster=lambda c: True)
    with context.test_request_context(json={"cloud": {"id": 99}}):
        with pytest.raises(InvalidUsageException, match="cannot change cloud project"):
            MagicCastleAPI().put(user, "test.example.org")
    background.assert_not_called()
