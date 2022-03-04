import pytest

from mchub.constants import MAGIC_CASTLE_SOURCE
from mchub.models.cloud.dns_manager import DnsManager

from ... mocks.configuration.config_mock import config_auth_none_mock  # noqa;
from ... test_helpers import *  # noqa;

def test_initialize_disallowed_domain():
    with pytest.raises(KeyError):
        DnsManager("invalid.com")


def test_get_available_domains():
    assert [
        "calculquebec.cloud",
        "c3.ca",
        "sub.example.com",
    ] == DnsManager.get_available_domains()


def test_get_environment_variables_with_dns_provider():
    assert DnsManager("calculquebec.cloud").get_environment_variables() == {
        "CLOUDFLARE_API_TOKEN": "EXAMPLE_TOKEN",
        "CLOUDFLARE_ZONE_API_TOKEN": "EXAMPLE_TOKEN",
        "CLOUDFLARE_DNS_API_TOKEN": "EXAMPLE_TOKEN",
    }
    assert DnsManager("c3.ca").get_environment_variables() == {
        "GOOGLE_CREDENTIALS": "/home/mcu/credentials/gcloud-service-account.json",
        "GCE_SERVICE_ACCOUNT_FILE": "/home/mcu/credentials/gcloud-service-account.json",
    }


def test_get_environment_variables_no_dns_provider():
    assert DnsManager("sub.example.com").get_environment_variables() == {}


def test_get_magic_castle_configuration_with_dns_provider():
    assert DnsManager("calculquebec.cloud").get_magic_castle_configuration() == {
        "dns": {
            "email": "you@example.com",
            "source": MAGIC_CASTLE_SOURCE["dns"]["cloudflare"],
            "name": "${module.openstack.cluster_name}",
            "domain": "${module.openstack.domain}",
            "public_instances": "${module.openstack.public_instances}",
            "ssh_private_key": "${module.openstack.ssh_private_key}",
            "sudoer_username": "${module.openstack.accounts.sudoer.username}",
        }
    }
    assert DnsManager("c3.ca").get_magic_castle_configuration() == {
        "dns": {
            "email": "you@example.com",
            "project": "your-project-name",
            "zone_name": "your-zone-name",
            "source": MAGIC_CASTLE_SOURCE["dns"]["gcloud"],
            "name": "${module.openstack.cluster_name}",
            "domain": "${module.openstack.domain}",
            "public_instances": "${module.openstack.public_instances}",
            "ssh_private_key": "${module.openstack.ssh_private_key}",
            "sudoer_username": "${module.openstack.accounts.sudoer.username}",
        }
    }


def test_get_magic_castle_configuration_no_dns_provider():
    assert DnsManager("sub.example.com").get_magic_castle_configuration() == {}
