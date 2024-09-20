import pytest
from mchub.models.auth_type import AuthType


"""
To use the configuration mock, simply import one of the two mock configurations, depending
on whether or not you need a configuration with SAML authentication enabled or not.

Using configuration mock with SAML authentication enabled:
from tests.mocks.configuration.config_mock import config_auth_saml_mock

Using configuration mock with no authentication:
from tests.mocks.configuration.config_mock import config_auth_none_mock

"""


BASE_CONFIGURATION = {
    "admins": ["the-admin@computecanada.ca"],
    "domains": {
        "calculquebec.cloud": {"dns_provider": "cf1"},
        "c3.ca": {"dns_provider": "gcloud1"},
    },
    "dns_providers": {
        "cf1": {
            "module": "cloudflare",
            "magic_castle_configuration": {},
            "environment_variables": {
                "CLOUDFLARE_API_TOKEN": "EXAMPLE_TOKEN",
                "CLOUDFLARE_ZONE_API_TOKEN": "EXAMPLE_TOKEN",
                "CLOUDFLARE_DNS_API_TOKEN": "EXAMPLE_TOKEN",
            },
        },
        "gcloud1": {
            "module": "gcloud",
            "magic_castle_configuration": {
                "project": "your-project-name",
                "zone_name": "your-zone-name",
            },
            "environment_variables": {
                "GOOGLE_CREDENTIALS": "/home/mcu/credentials/gcloud-service-account.json",
                "GCE_SERVICE_ACCOUNT_FILE": "/home/mcu/credentials/gcloud-service-account.json",
            },
        },
    },
}


@pytest.fixture(autouse=True)
def config_auth_saml_mock(mocker):
    configuration = BASE_CONFIGURATION
    configuration["auth_type"] = [AuthType.SAML]
    mocker.patch(
        "mchub.models.user.authenticated_user.config", new=configuration,
    )
    mocker.patch(
        "mchub.models.cloud.dns_manager.config", new=configuration,
    )
    mocker.patch(
        "mchub.resources.api_view.config", new=configuration,
    )


@pytest.fixture(autouse=True)
def config_auth_none_mock(mocker):
    configuration = BASE_CONFIGURATION
    configuration["auth_type"] = [AuthType.NONE]
    mocker.patch(
        "mchub.models.user.authenticated_user.config", new=configuration,
    )
    mocker.patch(
        "mchub.models.cloud.dns_manager.config", new=configuration,
    )
    mocker.patch(
        "mchub.resources.api_view.config", new=configuration,
    )
