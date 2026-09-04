from types import SimpleNamespace
from unittest.mock import Mock

from mchub.services.github_api import GithubStorage, MAGIC_CASTLE_REPOSITORY


def test_get_magic_castle_versions_filters_and_sorts_tags(mocker):
    mocker.patch(
        "mchub.services.github_api.get_config",
        return_value={"magic_castle_version_range": ">= 14.0.0, < 15.0.0"},
    )
    storage = GithubStorage.__new__(GithubStorage)
    storage.github = Mock()
    storage._magic_castle_versions_cache = {}
    repository = storage.github.get_repo.return_value
    repository.get_tags.return_value = [
        SimpleNamespace(name="15.0.0"),
        SimpleNamespace(name="14.0.0"),
        SimpleNamespace(name="not-a-version"),
        SimpleNamespace(name="14.2.0"),
        SimpleNamespace(name="14.1.3-beta.1"),
    ]

    assert storage.get_magic_castle_versions() == [
        "14.2.0",
        "14.1.3-beta.1",
        "14.0.0",
    ]
    storage.github.get_repo.assert_called_once_with(MAGIC_CASTLE_REPOSITORY)
