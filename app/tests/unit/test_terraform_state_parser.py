from models.terraform_state_parser import TerraformStateParser
from pathlib import Path
from os import path
import pytest
import json


def load_state(cluster_name):
    state_file_path = path.join(
        Path(__file__).parent.parent, "mock-clusters", cluster_name, "terraform.tfstate"
    )
    with open(state_file_path, "r") as terraform_state_file:
        return json.load(terraform_state_file)


@pytest.fixture
def valid_state():
    return load_state("valid-1")


@pytest.fixture
def empty_state():
    return load_state("empty")


@pytest.fixture
def missing_nodes_state():
    return load_state("missing-nodes")


def test_get_cores_valid(valid_state):
    parser = TerraformStateParser("valid-1", valid_state)
    assert parser.get_cores() == 4 + 4 + 2


def test_get_cores_empty(empty_state):
    parser = TerraformStateParser("empty", empty_state)
    assert parser.get_cores() == 0


def test_get_cores_missing_nodes(missing_nodes_state):
    parser = TerraformStateParser("missing-nodes", missing_nodes_state)
    assert parser.get_cores() == 0


def test_get_ram_valid(valid_state):
    parser = TerraformStateParser("valid-1", valid_state)
    assert parser.get_ram() == 6144 + 6144 + 3072


def test_get_ram_empty(empty_state):
    parser = TerraformStateParser("empty", empty_state)
    assert parser.get_ram() == 0


def test_get_ram_missing_nodes(missing_nodes_state):
    parser = TerraformStateParser("missing-nodes", missing_nodes_state)
    assert parser.get_ram() == 0


def test_get_volume_count_valid(valid_state):
    parser = TerraformStateParser("valid-1", valid_state)
    assert parser.get_volume_count() == 6


def test_get_volume_count_empty(empty_state):
    parser = TerraformStateParser("empty", empty_state)
    assert parser.get_volume_count() == 0


def test_get_volume_count_missing_nodes(missing_nodes_state):
    parser = TerraformStateParser("missing-nodes", missing_nodes_state)
    assert parser.get_volume_count() == 3


def test_get_volume_size_valid(valid_state):
    parser = TerraformStateParser("valid-1", valid_state)
    assert parser.get_volume_size() == 230


def test_get_volume_size_empty(empty_state):
    parser = TerraformStateParser("empty", empty_state)
    assert parser.get_volume_size() == 0


def test_get_volume_size_missing_nodes(missing_nodes_state):
    parser = TerraformStateParser("missing-nodes", missing_nodes_state)
    assert parser.get_volume_size() == 200


def test_get_os_floating_ips_valid(valid_state):
    parser = TerraformStateParser("valid-1", valid_state)
    assert parser.get_os_floating_ips() == ["100.101.102.103"]


def test_get_os_floating_ips_empty(empty_state):
    parser = TerraformStateParser("empty", empty_state)
    assert parser.get_os_floating_ips() == []


def test_get_os_floating_ips_missing_nodes(missing_nodes_state):
    parser = TerraformStateParser("missing-nodes", missing_nodes_state)
    assert parser.get_os_floating_ips() == ["100.101.102.103"]


def test_get_state_summary_valid(valid_state):
    parser = TerraformStateParser("valid-1", valid_state)
    assert parser.get_state_summary() == {
        "cluster_name": "valid-1",
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


def test_get_state_summary_empty(empty_state):
    parser = TerraformStateParser("empty", empty_state)
    assert parser.get_state_summary() == {
        "cluster_name": "empty",
        "domain": "",
        "image": "",
        "nb_users": 0,
        "instances": {
            "mgmt": {"type": "", "count": 0},
            "login": {"type": "", "count": 0},
            "node": {"type": "", "count": 0},
        },
        "storage": {
            "type": "nfs",
            "home_size": 0,
            "project_size": 0,
            "scratch_size": 0,
        },
        "public_keys": [],
        "guest_passwd": "",
        "os_floating_ips": [],
    }


def test_get_state_summary_missing_nodes(missing_nodes_state):
    parser = TerraformStateParser("missing-nodes", missing_nodes_state)
    assert parser.get_state_summary() == {
        "cluster_name": "missing-nodes",
        "nb_users": 10,
        "guest_passwd": "password-123",
        "storage": {
            "type": "nfs",
            "home_size": 100,
            "scratch_size": 50,
            "project_size": 50,
        },
        "instances": {
            "mgmt": {"type": "", "count": 0},
            "login": {"type": "", "count": 0},
            "node": {"type": "", "count": 0},
        },
        "domain": "example.com",
        "public_keys": ["ssh-rsa FAKE"],
        "image": "CentOS-7-x64-2019-07",
        "os_floating_ips": ["100.101.102.103"],
    }
