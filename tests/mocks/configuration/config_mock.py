import pytest


"""
To use the configuration mock, simply import one of the two mock configurations, depending
on whether or not you need a configuration with SAML authentication enabled or not.

Using configuration mock with SAML authentication enabled:
from tests.mocks.configuration.config_mock import config_auth_saml_mock

Using configuration mock with no authentication:
from tests.mocks.configuration.config_mock import config_auth_none_mock

"""


BASE_CONFIGURATION = {
    "token": "abcdefghijklmnopqrstuv123q123561",
    "admins": ["the-admin@computecanada.ca"],
    "cors_allowed_origins": ["https://hc-hub.example.com"],
    "domains": {
        "magic-castle.cloud": {"dns_provider": "cf1"},
        "mc.ca": {"dns_provider": "gcloud1"},
    },
    "dns_providers": {
        "cf1": {
            "module": "cloudflare",
            "magic_castle_configuration": {"email": "you@example.com"},
            "environment_variables": {
                "CLOUDFLARE_API_TOKEN": "EXAMPLE_TOKEN",
                "CLOUDFLARE_ZONE_API_TOKEN": "EXAMPLE_TOKEN",
                "CLOUDFLARE_DNS_API_TOKEN": "EXAMPLE_TOKEN",
            },
        },
        "gcloud1": {
            "module": "gcloud",
            "magic_castle_configuration": {
                "email": "you@example.com",
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
    from mchub.models.auth_type import AuthType
    configuration = BASE_CONFIGURATION.copy()
    configuration["auth_type"] = [AuthType.SAML]
    mocker.patch(
        "mchub.configuration._config",
        configuration,
    )


@pytest.fixture(autouse=True)
def config_auth_none_mock(mocker):
    from mchub.models.auth_type import AuthType
    configuration = BASE_CONFIGURATION.copy()
    configuration["auth_type"] = [AuthType.NONE]
    mocker.patch(
        "mchub.configuration._config",
        configuration,
    )
