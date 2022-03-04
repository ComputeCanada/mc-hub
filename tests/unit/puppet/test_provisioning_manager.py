import threading

import pytest

from requests.exceptions import ConnectionError

from mchub.models.puppet.provisioning_manager import ProvisioningManager
from mchub.exceptions.server_exception import PuppetTimeoutException

PROVISIONED_HOSTNAME = "provisioned.example.com"


@pytest.fixture(autouse=True)
def mock_max_provisioning_time(mocker):
    # MAX_PROVISIONING_TIME = 1 second
    mocker.patch("mchub.models.puppet.provisioning_manager.MAX_PROVISIONING_TIME", new=1)


@pytest.fixture(autouse=True)
def mock_poll_interval(mocker):
    # POLL_INTERVAL = 1 second
    mocker.patch("mchub.models.puppet.provisioning_manager.POLL_INTERVAL", new=1)


@pytest.fixture(autouse=True)
def mock_status_requests(mocker):
    def mock_get_request(url):
        class MockResponse:
            def __init__(self, status_code):
                self.status_code = status_code

        if url in [
            f"https://jupyter.{PROVISIONED_HOSTNAME}",
            f"https://ipa.{PROVISIONED_HOSTNAME}",
        ]:
            return MockResponse(200)
        raise ConnectionError

    mocker.patch("requests.get", new=mock_get_request)

