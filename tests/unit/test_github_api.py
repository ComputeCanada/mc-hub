from unittest.mock import Mock

from mchub.services.github_api import GithubStorage


def test_archive_repo():
    storage = GithubStorage.__new__(GithubStorage)
    storage.organization = "test-org"
    storage.github = Mock()
    organization = storage.github.get_organization.return_value
    repository = organization.get_repo.return_value

    storage.archive_repo("cluster.example.com")

    storage.github.get_organization.assert_called_once_with("test-org")
    organization.get_repo.assert_called_once_with(
        storage._get_repo_name("cluster.example.com")
    )
    repository.edit.assert_called_once_with(archived=True)
