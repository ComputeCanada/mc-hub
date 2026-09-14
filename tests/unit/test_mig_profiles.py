from unittest.mock import MagicMock, patch

import pytest
from marshmallow import ValidationError

from mchub.configuration import ConfigurationSchema
from mchub.models.cloud.cloud_manager import CloudManager


def test_additional_mig_profiles_are_optional_and_validated():
    field = ConfigurationSchema().fields["additional_mig_profiles"]
    assert field.load_default() == []
    assert field.deserialize(["1g.20gb", "2g.custom"]) == ["1g.20gb", "2g.custom"]
    for value in (["8g.80gb"], ["custom"], ["1g."], ["1g.has spaces"], "1g.20gb"):
        with pytest.raises(ValidationError):
            field.deserialize(value)


def test_available_resources_include_operator_profiles():
    cloud = CloudManager.__new__(CloudManager)
    cloud.manager = MagicMock()
    cloud.manager.available_resources = {"possible_resources": {}}
    with patch("mchub.models.cloud.cloud_manager.get_config", return_value={"additional_mig_profiles": ["1g.20gb"]}), \
         patch("mchub.models.cloud.cloud_manager.DnsManager.get_available_domains", return_value=[]), \
         patch("mchub.models.cloud.cloud_manager.get_github_storage") as storage:
        storage.return_value.get_magic_castle_versions.return_value = []
        assert cloud.available_resources["possible_resources"]["additional_mig_profiles"] == ["1g.20gb"]
