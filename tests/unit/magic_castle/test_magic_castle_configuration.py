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


def test_mc_version_is_written_to_terraform_variables():
    from mchub.models.magic_castle.magic_castle_configuration import (
        MagicCastleConfiguration,
    )

    config = deepcopy(CONFIG_DICT)
    config["mc_version"] = "14.1.2"

    var_tf = MagicCastleConfiguration("openstack", config).get_var_tf()

    assert var_tf["mc_version"] == "14.1.2"
    assert "version" not in var_tf


def test_version_is_not_accepted_as_mc_version():
    from mchub.models.magic_castle.magic_castle_configuration import (
        MagicCastleConfiguration,
    )

    config = deepcopy(CONFIG_DICT)
    config["version"] = config.pop("mc_version")

    with pytest.raises(ValidationError, match="mc_version"):
        MagicCastleConfiguration("openstack", config)


def test_aws_availability_zone_is_saved_and_written_to_terraform():
    from mchub.models.magic_castle.magic_castle_configuration import MagicCastleConfiguration

    config = MagicCastleConfiguration("aws", {**deepcopy(CONFIG_DICT), "availability_zone": "ca-central-1a"})
    assert dict(config)["availability_zone"] == "ca-central-1a"
    assert config.get_var_tf()["availability_zone"] == "ca-central-1a"


@pytest.mark.parametrize("zone", [None, ""])
def test_empty_aws_availability_zone_uses_terraform_default(zone):
    from mchub.models.magic_castle.magic_castle_configuration import MagicCastleConfiguration

    config = MagicCastleConfiguration("aws", {**deepcopy(CONFIG_DICT), "availability_zone": zone})
    assert "availability_zone" not in config.get_var_tf()
    assert "availability_zone" not in MagicCastleConfiguration("aws", deepcopy(CONFIG_DICT)).get_var_tf()


def test_openstack_does_not_accept_or_emit_aws_zone():
    from mchub.models.magic_castle.magic_castle_configuration import MagicCastleConfiguration

    config = MagicCastleConfiguration("openstack", {**deepcopy(CONFIG_DICT), "availability_zone": "ca-central-1a"})
    assert "availability_zone" not in config
    assert "availability_zone" not in config.get_var_tf()


def test_aws_data_volumes_are_passed_to_terraform():
    from mchub.models.magic_castle.magic_castle_configuration import MagicCastleConfiguration
    volumes = {"nfs": {name: {"size": 100} for name in ("home", "project", "scratch", "volume1")}}
    config = MagicCastleConfiguration("aws", {**deepcopy(CONFIG_DICT), "volumes": volumes})
    assert config.get_var_tf()["volumes"] == volumes


@pytest.mark.parametrize("zone", [None, "ca-central-1a"])
def test_terraform_variables_use_authoritative_aws_project_region(zone):
    from types import SimpleNamespace
    from mchub.models.magic_castle.magic_castle import MagicCastle
    from mchub.models.magic_castle.magic_castle_configuration import MagicCastleConfiguration

    config = MagicCastleConfiguration("aws", {**deepcopy(CONFIG_DICT), "region": "us-east-1", "availability_zone": zone})
    project = SimpleNamespace(provider="aws", env={"AWS_DEFAULT_REGION": "ca-central-1"})
    cluster = MagicCastle(SimpleNamespace(config=config, project=project, cluster_token=None))
    variables = cluster._get_var_tf()
    assert variables["region"] == "ca-central-1"
    assert variables.get("availability_zone") == zone
    assert "AWS_DEFAULT_REGION" not in variables
    project.env["AWS_DEFAULT_REGION"] = "us-west-2"
    assert cluster._get_var_tf()["region"] == "us-west-2"


def test_openstack_terraform_variables_do_not_include_aws_region():
    from types import SimpleNamespace
    from mchub.models.magic_castle.magic_castle import MagicCastle
    from mchub.models.magic_castle.magic_castle_configuration import MagicCastleConfiguration

    cluster = MagicCastle(SimpleNamespace(
        config=MagicCastleConfiguration("openstack", deepcopy(CONFIG_DICT)),
        project=SimpleNamespace(provider="openstack", env={}), cluster_token=None))
    assert "region" not in cluster._get_var_tf()
