from tests.test_helpers import *
from models.cloud.dns_manager import DnsManager
import pytest
from tests.mocks.configuration.config_mock import config_auth_none_mock


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
            "source": "/home/mcu/magic_castle-openstack-8.2//dns/cloudflare",
            "name": "${module.openstack.cluster_name}",
            "domain": "${module.openstack.domain}",
            "public_ip": "${module.openstack.ip}",
            "login_ids": "${module.openstack.login_ids}",
            "rsa_public_key": "${module.openstack.rsa_public_key}",
            "ssh_private_key": "${module.openstack.ssh_private_key}",
            "sudoer_username": "${module.openstack.sudoer_username}",
        }
    }
    assert DnsManager("c3.ca").get_magic_castle_configuration() == {
        "dns": {
            "email": "you@example.com",
            "project": "your-project-name",
            "zone_name": "your-zone-name",
            "source": "/home/mcu/magic_castle-openstack-8.2//dns/gcloud",
            "name": "${module.openstack.cluster_name}",
            "domain": "${module.openstack.domain}",
            "public_ip": "${module.openstack.ip}",
            "login_ids": "${module.openstack.login_ids}",
            "rsa_public_key": "${module.openstack.rsa_public_key}",
            "ssh_private_key": "${module.openstack.ssh_private_key}",
            "sudoer_username": "${module.openstack.sudoer_username}",
        }
    }


def test_get_magic_castle_configuration_no_dns_provider():
    assert DnsManager("sub.example.com").get_magic_castle_configuration() == {}
