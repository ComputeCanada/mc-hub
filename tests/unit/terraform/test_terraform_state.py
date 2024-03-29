import pytest
import json

import tests


from os import path
from mchub.models.terraform.terraform_state import TerraformState

from ...mocks.configuration.config_mock import config_auth_none_mock  # noqa;


def load_state(hostname):
    state_file_path = path.join(
        path.dirname(tests.__file__),
        "data",
        "mock-clusters",
        hostname,
        "terraform.tfstate",
    )
    with open(state_file_path, "r") as terraform_state_file:
        return json.load(terraform_state_file)


@pytest.fixture
def valid_state():
    return load_state("valid1.magic-castle.cloud")


@pytest.fixture
def empty_state():
    return load_state("empty-state.magic-castle.cloud")


@pytest.fixture
def missing_nodes_state():
    return load_state("missingnodes.mc.ca")


def test_instance_count_valid(valid_state):
    state = TerraformState(valid_state)
    assert state.instance_count == 3


def test_instance_count_empty(empty_state):
    state = TerraformState(empty_state)
    assert state.instance_count == 0


def test_instance_count_missing_nodes(missing_nodes_state):
    state = TerraformState(missing_nodes_state)
    assert state.instance_count == 0


def test_cores_valid(valid_state):
    state = TerraformState(valid_state)
    assert state.cores == 4 + 4 + 2


def test_cores_empty(empty_state):
    state = TerraformState(empty_state)
    assert state.cores == 0


def test_cores_missing_nodes(missing_nodes_state):
    state = TerraformState(missing_nodes_state)
    assert state.cores == 0


def test_ram_valid(valid_state):
    state = TerraformState(valid_state)
    assert state.ram == 6144 + 6144 + 3072


def test_ram_empty(empty_state):
    state = TerraformState(empty_state)
    assert state.ram == 0


def test_get_ram_missing_nodes(missing_nodes_state):
    state = TerraformState(missing_nodes_state)
    assert state.ram == 0


def test_volume_count_valid(valid_state):
    state = TerraformState(valid_state)
    assert state.volume_count == 3


def test_volume_count_empty(empty_state):
    state = TerraformState(empty_state)
    assert state.volume_count == 0


def test_volume_count_missing_nodes(missing_nodes_state):
    state = TerraformState(missing_nodes_state)
    assert state.volume_count == 3


def test_volume_size_valid(valid_state):
    state = TerraformState(valid_state)
    assert state.volume_size == 200


def test_volume_size_empty(empty_state):
    state = TerraformState(empty_state)
    assert state.volume_size == 0


def test_volume_size_missing_nodes(missing_nodes_state):
    state = TerraformState(missing_nodes_state)
    assert state.volume_size == 200
