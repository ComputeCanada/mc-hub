from unittest.mock import Mock

import pytest
from github import GithubException

from mchub.services.github_api import GithubStorage


@pytest.mark.parametrize("status, missing_ok, ignored", [(404, True, True), (404, False, False),
                                                       (403, True, False), (500, True, False)])
def test_missing_repository_cleanup(status, missing_ok, ignored):
    storage = GithubStorage.__new__(GithubStorage)
    storage.organization = "test-org"
    storage.github = Mock()
    storage.github.get_organization.return_value.get_repo.side_effect = GithubException(status, "failure")
    if ignored:
        storage.archive_repo("failed.example.org", missing_ok=missing_ok)
    else:
        with pytest.raises(GithubException):
            storage.archive_repo("failed.example.org", missing_ok=missing_ok)


def test_cleanup_still_archives_a_repository_created_before_failure():
    storage = GithubStorage.__new__(GithubStorage)
    storage.organization = "test-org"
    storage.github = Mock()
    repo = storage.github.get_organization.return_value.get_repo.return_value
    storage.archive_repo("failed.example.org", missing_ok=True)
    repo.edit.assert_called_once_with(archived=True)
    repo.edit.side_effect = GithubException(404, "failure")
    with pytest.raises(GithubException):
        storage.archive_repo("failed.example.org", missing_ok=True)
