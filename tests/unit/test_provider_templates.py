from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from flask import Flask
from marshmallow import ValidationError

from mchub.configuration import ConfigurationSchema
from mchub.exceptions.server_exception import GithubStorageException
from mchub.models.cloud.project import Provider
from mchub.resources.project_api import ProjectAPI
from mchub.services.github_api import GithubStorage, get_provider_template


@pytest.mark.parametrize("provider", [Provider.AWS, Provider.OPENSTACK])
def test_template_selected_by_provider(mocker, provider):
    templates = {"aws": "https://github.com/operator/aws", "openstack": "https://github.com/operator/openstack"}
    mocker.patch("mchub.services.github_api.get_config", return_value={"github_templates": templates})
    assert get_provider_template(provider) == templates[provider.value]


def test_missing_provider_template_reports_operator_setting(mocker):
    mocker.patch("mchub.services.github_api.get_config", return_value={"github_templates": {}})
    with pytest.raises(GithubStorageException, match="github_templates in configuration.json"):
        get_provider_template(Provider.AWS)


@pytest.mark.parametrize("suffix", ["", "/", ".git"])
def test_template_url_resolves_to_github_repository(suffix):
    url = f"https://github.com/operator/aws-template{suffix}"
    config = ConfigurationSchema().load({"auth_type": ["NONE"], "github_templates": {"aws": url}}, partial=True)
    storage = GithubStorage.__new__(GithubStorage)
    storage.organization = "deployment-org"
    storage.github = Mock()
    storage.validate_template(config["github_templates"]["aws"])
    storage.github.get_repo.assert_called_once_with("operator/aws-template")


@pytest.mark.parametrize("templates", [
    {"aws": "owner/repo"}, {"aws": "https://example.com/owner/repo"},
    {"aws": "https://github.com/owner/repo/tree/main"}, {"aws": ""},
    {"unknown": "https://github.com/owner/repo"},
])
def test_invalid_template_configuration_rejected(templates):
    with pytest.raises(ValidationError):
        ConfigurationSchema().load({"github_templates": templates}, partial=True)


def test_project_edit_cannot_override_template(mocker):
    project = SimpleNamespace(provider=Provider.OPENSTACK, github_template="legacy")
    mocker.patch("mchub.resources.project_api.db").session.get.return_value = project
    storage = mocker.patch("mchub.resources.project_api.get_github_storage")
    user = SimpleNamespace(projects=[project], is_project_admin=lambda p: True, domain="example.org")
    with Flask(__name__).test_request_context(json={"github_template": "user/override"}):
        ProjectAPI().patch(user, 1)
    assert project.github_template == "legacy"
    storage.assert_not_called()
