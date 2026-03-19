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


def test_properties():
    from mchub.models.magic_castle.magic_castle_configuration import (
        MagicCastleConfiguration,
    )

    config = MagicCastleConfiguration("openstack", CONFIG_DICT)
    assert config.cluster_name == "foo-123"
    assert config.domain == "magic-castle.cloud"