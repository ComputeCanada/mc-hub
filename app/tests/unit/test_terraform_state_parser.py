from models.terraform_state_parser import TerraformStateParser
from pathlib import Path
from os import path
import pytest
import json


@pytest.fixture
def fake_state():
    state_file_path = path.join(
        Path(__file__).parent.parent, "fake-cluster", "terraform.tfstate"
    )
    with open(state_file_path, "r") as terraform_state_file:
        return json.load(terraform_state_file)


def test_get_used_cores(fake_state):
    parser = TerraformStateParser(fake_state)
    assert parser.get_used_cores() == 4 + 4 + 2


def test_get_used_ram(fake_state):
    parser = TerraformStateParser(fake_state)
    assert parser.get_used_ram() == 6144 + 6144 + 3072


def test_get_state_summary(fake_state):
    parser = TerraformStateParser(fake_state)
    assert parser.get_state_summary() == {
        "cluster_name": "fake-cluster",
        "nb_users": 10,
        "guest_passwd": "password-123",
        "storage": {
            "type": "nfs",
            "home_size": 100,
            "scratch_size": 50,
            "project_size": 50,
        },
        "instances": {
            "mgmt": {"type": "p4-6gb", "count": 1},
            "login": {"type": "p4-6gb", "count": 1},
            "node": {"type": "p2-3gb", "count": 1},
        },
        "domain": "example.com",
        "public_keys": ["ssh-rsa FAKE"],
        "image": "CentOS-7-x64-2019-07",
        "os_floating_ips": ["100.101.102.103"],
    }
