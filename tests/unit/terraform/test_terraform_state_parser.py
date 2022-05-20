import pytest
import json

import tests


from os import path
from mchub.models.terraform.terraform_state_parser import TerraformStateParser

from ... mocks.configuration.config_mock import config_auth_none_mock  # noqa;


def load_state(hostname):
    state_file_path = path.join(
        path.dirname(tests.__file__), "mock-clusters", hostname, "terraform.tfstate"
    )
    with open(state_file_path, "r") as terraform_state_file:
        return json.load(terraform_state_file)


@pytest.fixture
def valid_state():
    return load_state("valid1.calculquebec.cloud")


@pytest.fixture
def empty_state():
    return load_state("empty.calculquebec.cloud")


@pytest.fixture
def missing_nodes_state():
    return load_state("missingnodes.c3.ca")


def test_instance_count_valid(valid_state):
    parser = TerraformStateParser(valid_state)
    assert parser.instance_count == 3


def test_instance_count_empty(empty_state):
    parser = TerraformStateParser(empty_state)
    assert parser.instance_count == 0


def test_instance_count_missing_nodes(missing_nodes_state):
    parser = TerraformStateParser(missing_nodes_state)
    assert parser.instance_count == 0


def test_cores_valid(valid_state):
    parser = TerraformStateParser(valid_state)
    assert parser.cores == 4 + 4 + 2


def test_cores_empty(empty_state):
    parser = TerraformStateParser(empty_state)
    assert parser.cores == 0


def test_cores_missing_nodes(missing_nodes_state):
    parser = TerraformStateParser(missing_nodes_state)
    assert parser.cores == 0


def test_ram_valid(valid_state):
    parser = TerraformStateParser(valid_state)
    assert parser.ram == 6144 + 6144 + 3072


def test_ram_empty(empty_state):
    parser = TerraformStateParser(empty_state)
    assert parser.ram == 0


def test_get_ram_missing_nodes(missing_nodes_state):
    parser = TerraformStateParser(missing_nodes_state)
    assert parser.ram == 0


def test_volume_count_valid(valid_state):
    parser = TerraformStateParser(valid_state)
    assert parser.volume_count == 3


def test_volume_count_empty(empty_state):
    parser = TerraformStateParser(empty_state)
    assert parser.volume_count == 0


def test_volume_count_missing_nodes(missing_nodes_state):
    parser = TerraformStateParser(missing_nodes_state)
    assert parser.volume_count == 3


def test_volume_size_valid(valid_state):
    parser = TerraformStateParser(valid_state)
    assert parser.volume_size == 200


def test_volume_size_empty(empty_state):
    parser = TerraformStateParser(empty_state)
    assert parser.volume_size == 0


def test_volume_size_missing_nodes(missing_nodes_state):
    parser = TerraformStateParser(missing_nodes_state)
    assert parser.volume_size == 200

