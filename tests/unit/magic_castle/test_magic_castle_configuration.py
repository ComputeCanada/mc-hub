import pytest

from copy import deepcopy
from os import path

from marshmallow.exceptions import ValidationError

from ...test_helpers import (
    generate_test_clusters,
    mock_clusters_path,
    MOCK_CLUSTERS_PATH,
)
from ...mocks.configuration.config_mock import config_auth_none_mock as config_mock

from ...data import CONFIG_DICT, CLUSTERS_CONFIG


def test_constructor_valid():
    from mchub.models.magic_castle.magic_castle_configuration import (
        MagicCastleConfiguration,
    )

    config = deepcopy(CONFIG_DICT)
    assert MagicCastleConfiguration("openstack", config) == config


def test_constructor_empty_hieradata_valid():
    from mchub.models.magic_castle.magic_castle_configuration import (
        MagicCastleConfiguration,
    )

    config = deepcopy(CONFIG_DICT)
    config["hieradata"] = ""
    assert MagicCastleConfiguration("openstack", config) == config


def test_constructor_invalid_cluster_name():
    from mchub.models.magic_castle.magic_castle_configuration import (
        MagicCastleConfiguration,
    )

    config = deepcopy(CONFIG_DICT)
    config["cluster_name"] = "foo!"
    with pytest.raises(ValidationError):
        MagicCastleConfiguration("openstack", config)

    config = deepcopy(CONFIG_DICT)
    config["cluster_name"] = "foo_underscore"
    with pytest.raises(ValidationError):
        MagicCastleConfiguration("openstack", config)


def test_constructor_invalid_domain():
    from mchub.models.magic_castle.magic_castle_configuration import (
        MagicCastleConfiguration,
    )

    config = deepcopy(CONFIG_DICT)
    config["domain"] = "invalid.cloud"
    with pytest.raises(ValidationError):
        MagicCastleConfiguration("openstack", config)


def test_get_from_main_file_valid():
    from mchub.models.magic_castle.magic_castle_configuration import (
        MagicCastleConfiguration,
    )

    config = MagicCastleConfiguration.get_from_main_file(
        path.join(MOCK_CLUSTERS_PATH, "missingnodes.mc.ca", "main.tf.json")
    )
    assert config == CLUSTERS_CONFIG["missingnodes.mc.ca"]


def test_get_from_main_file_not_found():
    from mchub.models.magic_castle.magic_castle_configuration import (
        MagicCastleConfiguration,
    )

    with pytest.raises(FileNotFoundError):
        MagicCastleConfiguration.get_from_main_file("empty")
    with pytest.raises(FileNotFoundError):
        MagicCastleConfiguration.get_from_main_file("non-existing")


def test_write():
    from mchub.models.magic_castle.magic_castle_configuration import (
        MagicCastleConfiguration,
    )

    CONFIG_DICT = {
        "cluster_name": "missingnodes",
        "domain": "mc.ca",
        "image": "Rocky-8.7-x64-2023-02",
        "nb_users": 30,
        "instances": {
            "mgmt": {"type": "", "count": 1, "tags": ["mgmt", "nfs", "puppet"]},
            "login": {"type": "", "count": 1, "tags": ["login", "proxy", "public"]},
            "node": {"type": "", "count": 12, "tags": ["node"]},
        },
        "volumes": {
            "nfs": {
                "home": {"size": 400},
                "project": {"size": 12},
                "scratch": {"size": 50},
            }
        },
        "public_keys": ["ssh-rsa FOOBAR"],
        "hieradata": "",
        "guest_passwd": "",
    }

    modified_config = MagicCastleConfiguration("openstack", CONFIG_DICT)
    path_ = path.join(MOCK_CLUSTERS_PATH, "missingnodes.mc.ca", "main.tf.json")
    modified_config.write(path_)
    saved_config = MagicCastleConfiguration.get_from_main_file(path_)
    assert saved_config == CONFIG_DICT


def test_properties():
    from mchub.models.magic_castle.magic_castle_configuration import (
        MagicCastleConfiguration,
    )

    config = MagicCastleConfiguration("openstack", CONFIG_DICT)
    assert config.cluster_name == "foo-123"
    assert config.domain == "magic-castle.cloud"
