from unittest.mock import call

from requests.exceptions import SSLError

from mchub.models.puppet.provisioning_manager import ProvisioningManager


def test_check_online_verifies_service_certificates(mocker):
    get = mocker.patch(
        "mchub.models.puppet.provisioning_manager.requests.get",
        return_value=mocker.Mock(status_code=200),
    )

    assert ProvisioningManager.check_online("example.com") is True
    assert get.call_args_list == [
        call("https://jupyter.example.com", timeout=0.1, verify=True),
        call("https://ipa.example.com", timeout=0.1, verify=True),
        call("https://metrix.example.com", timeout=0.1, verify=True),
        call("https://mokey.example.com", timeout=0.1, verify=True),
    ]


def test_check_online_treats_invalid_certificate_as_not_ready(mocker):
    get = mocker.patch(
        "mchub.models.puppet.provisioning_manager.requests.get",
        side_effect=SSLError("certificate verify failed"),
    )

    assert ProvisioningManager.check_online("example.com") is False
    assert get.call_count == 4
