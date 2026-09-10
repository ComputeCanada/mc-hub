import pytest

from mchub.database import db
from mchub.models.cloud.project import Project
from tests.data import ALICE_HEADERS, BOB_HEADERS
from tests.test_helpers import app, client, generate_test_clusters, mock_clusters_path  # noqa: F401
from tests.mocks.configuration.config_mock import config_auth_saml_mock as config_mock  # noqa: F401


@pytest.fixture
def services(mocker):
    terraform = mocker.patch("mchub.resources.project_api.get_terraform_cloud").return_value
    terraform.create_project.return_value = "new-tf-project"
    mocker.patch("mchub.resources.project_api.get_github_storage")
    mocker.patch("mchub.resources.project_api.AWSManager.validate_project")
    mocker.patch("mchub.resources.project_api.OpenStackManager.subnets", return_value=[{"id": "subnet"}])
    return terraform


@pytest.fixture(params=["aws", "openstack"])
def payload(request):
    env = {"AWS_ACCESS_KEY_ID": "key", "AWS_SECRET_ACCESS_KEY": "secret", "AWS_DEFAULT_REGION": "ca-central-1"}
    if request.param == "openstack":
        env = {"OS_AUTH_URL": "https://cloud.example.org:5000/v3", "OS_APPLICATION_CREDENTIAL_ID": "a" * 32,
               "OS_APPLICATION_CREDENTIAL_SECRET": "s" * 86, "OS_SUBNET_ID": "subnet"}
    return {"name": "personal-cloud", "provider": request.param, "env": env}


@pytest.mark.parametrize("new_user", [False, True])
def test_regular_user_registers_and_manages_only_their_project(client, services, payload, new_user):
    headers = dict(ALICE_HEADERS)
    if new_user:
        headers["eduPersonPrincipalName"] = "new-user@example.org"
    assert client.get("/api/users/me", headers=headers).json["is_admin"] is False
    response = client.post("/api/projects", headers=headers, json=payload)
    assert response.status_code == 200, response.json
    project_id = response.json["id"]
    project = db.session.get(Project, project_id)
    assert [u.scoped_id for u in project.admins] == [headers["eduPersonPrincipalName"]]
    services.create_project.assert_called_once_with(f"{headers['eduPersonPrincipalName'].split('@')[0]}-personal-cloud", agent_pool_name=None)
    assert response.json["name"] == "personal-cloud"
    assert project.tfcloud_project_name == services.create_project.call_args.args[0]
    assert project_id in [p["id"] for p in client.get("/api/projects", headers=headers).json]
    url = f"/api/projects/{project_id}"
    assert client.get(url, headers=BOB_HEADERS).status_code != 200
    assert client.patch(url, headers=BOB_HEADERS, json={"add": ["someone"]}).status_code != 200
    assert client.delete(url, headers=BOB_HEADERS).status_code != 200
    assert client.patch(url, headers=headers, json={"add": [BOB_HEADERS["eduPersonPrincipalName"]]}).status_code == 200
    assert client.get(url, headers=BOB_HEADERS).json["admin"] is False
    assert client.patch(url, headers=BOB_HEADERS, json={"add_admins": [BOB_HEADERS["eduPersonPrincipalName"]]}).status_code != 200
    assert client.patch(url, headers=headers, json={"agent_pool_name": "private"}).status_code == 403
    services.update_project.assert_not_called()
    assert client.delete(url, headers=headers).status_code == 200


def test_registration_requires_authentication(client, services, payload):
    assert client.post("/api/projects", json=payload).status_code != 200
    services.create_project.assert_not_called()


@pytest.mark.parametrize("scoped_id", ["alice@computecanada.ca", "the-admin@computecanada.ca"])
def test_user_supplied_agent_pool_is_rejected(client, services, payload, scoped_id):
    headers = {**ALICE_HEADERS, "eduPersonPrincipalName": scoped_id}
    payload["agent_pool_name"] = "private"
    assert client.post("/api/projects", headers=headers, json=payload).status_code == 403
    services.create_project.assert_not_called()
    del payload["agent_pool_name"]
    response = client.post("/api/projects", headers=headers, json=payload)
    assert response.status_code == 200, response.json
    assert client.patch(f"/api/projects/{response.json['id']}", headers=headers, json={"agent_pool_name": "other"}).status_code == 403
    services.update_project.assert_not_called()


def test_service_token_cannot_register_without_user_identity(client, services, payload, mocker):
    from mchub.configuration import get_config
    from mchub.models.auth_type import AuthType

    config = get_config()
    mocker.patch.dict(config, {"auth_type": [AuthType.SAML, AuthType.TOKEN]})
    response = client.post("/api/projects", headers={"Authorization": f"token {config['token']}"}, json=payload)
    assert response.status_code == 403
    services.create_project.assert_not_called()


def test_discovery_requires_authentication_but_not_hub_admin(client, services, payload, mocker):
    mocker.patch("mchub.resources.project_api.AWSManager.regions", return_value=["ca-central-1"])
    route = "/api/projects/aws/regions" if payload["provider"] == "aws" else "/api/projects/openstack/subnets"
    assert client.post(route, json={"env": payload["env"]}).status_code != 200
    response = client.post(route, headers=ALICE_HEADERS, json={"env": payload["env"]})
    assert response.status_code == 200, response.json


def test_project_names_are_unique_for_username_across_providers(client, services, payload):
    response = client.post("/api/projects", headers=ALICE_HEADERS, json=payload)
    assert response.status_code == 200
    services.reset_mock()
    # Change provider while retaining the same username and display name.
    payload["provider"] = "aws" if payload["provider"] == "openstack" else "openstack"
    response = client.post("/api/projects", headers=ALICE_HEADERS, json=payload)
    assert response.status_code == 409
    assert response.json == {"message": "Project name is already in use for your username. Choose another name."}
    services.create_project.assert_not_called()
    services.set_project_variable_set.assert_not_called()


def test_different_users_can_reuse_display_name(client, services, payload):
    for headers, terraform_name in [(ALICE_HEADERS, "alice-personal-cloud"), (BOB_HEADERS, "bob12-bobby-personal-cloud")]:
        response = client.post("/api/projects", headers=headers, json=payload)
        assert response.status_code == 200, response.json
        assert response.json["name"] == "personal-cloud"
        services.create_project.assert_called_with(terraform_name, agent_pool_name=None)


def test_concurrent_duplicate_returns_conflict_and_rolls_back(client, services, payload):
    def concurrent_registration(*args, **kwargs):
        db.session.add(Project(name=payload["name"], tfcloud_project_name="alice-personal-cloud", provider="aws", env={}, github_template="template",
                               tfcloud_project_id="other-project"))
        db.session.commit()
        return "new-tf-project"

    services.create_project.side_effect = concurrent_registration
    response = client.post("/api/projects", headers=ALICE_HEADERS, json=payload)
    assert response.status_code == 409
    projects = db.session.scalars(db.select(Project).where(Project.name == payload["name"])).all()
    assert len(projects) == 1
    assert projects[0].tfcloud_project_id == "other-project"


@pytest.mark.parametrize("name", ["x" * 35, "invalid/name", "trailing "])
def test_invalid_combined_terraform_name_rejected_before_external_calls(client, services, payload, name):
    payload["name"] = name
    response = client.post("/api/projects", headers=ALICE_HEADERS, json=payload)
    assert response.status_code == 400
    services.create_project.assert_not_called()


def test_existing_terraform_name_is_reserved(client, services, payload):
    db.session.add(Project(name="alice-personal-cloud", tfcloud_project_id="legacy", provider="aws", env={}, github_template="template"))
    db.session.commit()
    response = client.post("/api/projects", headers=ALICE_HEADERS, json=payload)
    assert response.status_code == 409
    services.create_project.assert_not_called()


def test_approved_cloud_list_requires_authentication_and_exposes_only_cloud_fields(client, mocker):
    from mchub.configuration import get_config
    mocker.patch.dict(get_config(), {"openstack_clouds": [{"name": "Vetted Cloud", "auth_url": "https://vetted.example.org/v3", "secret": "hidden"}]})
    url = "/api/projects/openstack/clouds"
    assert client.get(url).status_code != 200
    result = client.get(url, headers=ALICE_HEADERS)
    assert result.status_code == 200
    assert result.json == {"clouds": [{"name": "Vetted Cloud", "auth_url": "https://vetted.example.org/v3"}]}


@pytest.mark.parametrize("url", ["https://untrusted.example.org/v3", "https://cloud.example.org.evil.test:5000/v3", "https://cloud.example.org:5000/v3/../admin"])
def test_openstack_url_must_be_approved_for_registration_and_discovery(client, services, mocker, url):
    validate = mocker.patch("mchub.resources.project_api.OpenStackManager")
    env = {"OS_AUTH_URL": url, "OS_APPLICATION_CREDENTIAL_ID": "a" * 32,
           "OS_APPLICATION_CREDENTIAL_SECRET": "s" * 86}
    result = client.post("/api/projects", headers=ALICE_HEADERS, json={"name": "unapproved", "provider": "openstack", "env": env})
    assert result.status_code == 403
    result = client.post("/api/projects/openstack/subnets", headers=ALICE_HEADERS, json={"env": env})
    assert result.status_code == 403
    validate.assert_not_called()
    services.create_project.assert_not_called()


def test_unapproved_credential_rotation_rejected_before_external_mutation(client, services):
    project = db.session.scalar(db.select(Project).where(Project.name == "project-alice"))
    original_env = project.env.copy()
    env = {**original_env, "OS_AUTH_URL": "https://untrusted.example.org/v3"}
    result = client.patch(f"/api/projects/{project.id}", headers=ALICE_HEADERS, json={"env": env})
    assert result.status_code == 403
    assert project.env == original_env
    services.replace_project_variable_set.assert_not_called()


def test_no_configured_clouds_disables_openstack_discovery(client, services, mocker):
    from mchub.configuration import get_config
    mocker.patch.dict(get_config(), {"openstack_clouds": []})
    assert client.get("/api/projects/openstack/clouds", headers=ALICE_HEADERS).json == {"clouds": []}
    env = {"OS_AUTH_URL": "https://cloud.example.org:5000/v3", "OS_APPLICATION_CREDENTIAL_ID": "a" * 32,
           "OS_APPLICATION_CREDENTIAL_SECRET": "s" * 86}
    assert client.post("/api/projects/openstack/subnets", headers=ALICE_HEADERS, json={"env": env}).status_code == 403


@pytest.mark.parametrize("agent_pool", [None, "research-agents"])
def test_agent_pool_comes_from_openstack_cloud_config(client, services, payload, mocker, agent_pool):
    from mchub.configuration import get_config
    clouds = [{"name": "Research", "auth_url": "https://cloud.example.org:5000/v3", "agent_pool_name": agent_pool}]
    mocker.patch.dict(get_config(), {"openstack_clouds": clouds})
    result = client.post("/api/projects", headers=ALICE_HEADERS, json=payload)
    assert result.status_code == 200, result.json
    expected = agent_pool if payload["provider"] == "openstack" else None
    services.create_project.assert_called_once_with("alice-personal-cloud", agent_pool_name=expected)
    assert "agent_pool_name" not in client.get("/api/projects/openstack/clouds", headers=ALICE_HEADERS).json["clouds"][0]
    # Saving credentials applies the operator setting, including resetting to default.
    clouds[0]["agent_pool_name"] = None if agent_pool else "replacement-agents"
    result = client.patch(f"/api/projects/{result.json['id']}", headers=ALICE_HEADERS, json={"env": payload["env"]})
    assert result.status_code == 200, result.json
    if payload["provider"] == "openstack":
        services.update_project.assert_called_once_with("new-tf-project", clouds[0]["agent_pool_name"])
    else:
        services.update_project.assert_not_called()
