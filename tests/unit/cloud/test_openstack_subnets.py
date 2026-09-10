from types import SimpleNamespace

import pytest
from flask import Flask
from openstack.exceptions import SDKException

from mchub.exceptions.invalid_usage_exception import InvalidUsageException
from mchub.models.cloud.openstack_manager import OpenStackManager
from mchub.models.cloud.project import Project, Provider
from mchub.resources.project_api import OpenStackSubnetsAPI, ProjectAPI

ENV = {"OS_AUTH_URL": "https://cloud.example.org:5000/v3", "OS_APPLICATION_CREDENTIAL_ID": "a" * 32,
       "OS_APPLICATION_CREDENTIAL_SECRET": "s" * 86, "OS_SUBNET_ID": "subnet-b"}


def test_discovery_uses_credentials_and_returns_named_internal_ipv4_subnets(mocker):
    connect = mocker.patch("mchub.models.cloud.openstack_manager.openstack.connect")
    network = connect.return_value.network
    network.networks.return_value = [
        SimpleNamespace(id="internal", is_router_external=False),
        SimpleNamespace(id="external", is_router_external=True),
    ]
    network.subnets.return_value = [
        SimpleNamespace(id="subnet-b", name="Alpha", ip_version=4, network_id="internal"),
        SimpleNamespace(id="subnet-a", name="Beta", ip_version=4, network_id="internal"),
        SimpleNamespace(id="ipv6", name="IPv6", ip_version=6, network_id="internal"),
        SimpleNamespace(id="public", name="Public", ip_version=4, network_id="external"),
        SimpleNamespace(id="unknown", name="Unknown network", ip_version=4, network_id="missing"),
        SimpleNamespace(id="unnamed", name="", ip_version=4, network_id="internal"),
    ]
    with Flask(__name__).test_request_context(json={"env": ENV}):
        assert OpenStackSubnetsAPI().post(SimpleNamespace(is_admin=True)) == {"subnets": [
            {"id": "subnet-b", "name": "Alpha"}, {"id": "subnet-a", "name": "Beta"},
            {"id": "unnamed", "name": "Unnamed subnet"},
        ]}
    network.networks.assert_called_once_with(is_router_external=False)
    network.subnets.assert_called_once_with(ip_version=4)
    connect.assert_called_once_with(auth_url=ENV["OS_AUTH_URL"], application_credential_id="a" * 32,
                                    application_credential_secret="s" * 86, auth_type="v3applicationcredential")


@pytest.mark.parametrize("admin,env", [(False, ENV), (True, {})])
def test_discovery_rejects_unauthorized_or_missing_credentials(mocker, admin, env):
    connect = mocker.patch("mchub.models.cloud.openstack_manager.openstack.connect")
    with Flask(__name__).test_request_context(json={"env": env}):
        with pytest.raises(InvalidUsageException):
            OpenStackSubnetsAPI().post(SimpleNamespace(is_admin=admin))
    connect.assert_not_called()


def test_discovery_failure_is_safe(mocker):
    mocker.patch("mchub.models.cloud.openstack_manager.openstack.connect", side_effect=SDKException("secret"))
    with pytest.raises(InvalidUsageException, match="Unable to load OpenStack subnets") as error:
        OpenStackManager(Project(provider=Provider.OPENSTACK, env=ENV)).subnets()
    assert "secret" not in str(error.value)


def test_invalid_subnet_rejected_before_project_creation(mocker):
    mocker.patch.object(OpenStackManager, "subnets", return_value=[{"id": "subnet-a", "name": "Alpha"}])
    terraform = mocker.patch("mchub.resources.project_api.get_terraform_cloud")
    with Flask(__name__).test_request_context(json={"provider": "openstack", "env": ENV, "name": "test", "github_template": ""}):
        with pytest.raises(InvalidUsageException, match="Select an available"):
            ProjectAPI().post(SimpleNamespace(is_admin=True))
    terraform.assert_not_called()


def test_credential_rotation_preserves_subnet(mocker):
    project = SimpleNamespace(provider=Provider.OPENSTACK, env=ENV.copy(), name="test", tfcloud_project_id="p")
    mocker.patch("mchub.resources.project_api.db").session.get.return_value = project
    mocker.patch("mchub.resources.project_api.get_terraform_cloud")
    credentials = {k: v for k, v in ENV.items() if k != "OS_SUBNET_ID"}
    with Flask(__name__).test_request_context(json={"env": credentials}):
        ProjectAPI().patch(SimpleNamespace(projects=[project], is_project_admin=lambda p: True, domain="example.org"), 1)
    assert project.env["OS_SUBNET_ID"] == "subnet-b"


def test_project_creation_persists_selected_subnet(mocker):
    from mchub.models.user import UserORM

    mocker.patch.object(OpenStackManager, "subnets", return_value=[{"id": "subnet-b", "name": "Beta"}])
    database = mocker.patch("mchub.resources.project_api.db")
    terraform = mocker.patch("mchub.resources.project_api.get_terraform_cloud").return_value
    terraform.create_project.return_value = "tf-project"
    user = SimpleNamespace(is_admin=True, orm=UserORM(id=1, scoped_id="admin@example.org"))
    with Flask(__name__).test_request_context(json={"provider": "openstack", "env": ENV, "name": "test", "github_template": ""}):
        _, status = ProjectAPI().post(user)
    assert status == 200
    project = database.session.add.call_args.args[0]
    assert project.env["OS_SUBNET_ID"] == "subnet-b"
    database.session.commit.assert_called_once()
