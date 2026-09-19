from unittest.mock import Mock
import pytest
from github import GithubException
from mchub.exceptions.server_exception import GithubStorageException

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


@pytest.mark.parametrize("trigger_run", [False, True])
def test_write_creates_deployment_tag_only_when_requested(trigger_run):
    storage = GithubStorage.__new__(GithubStorage)
    storage.organization = "test-org"
    storage.github = Mock()
    repository = storage.github.get_organization.return_value.get_repo.return_value
    repository.get_contents.return_value = Mock(path="terraform.tfvars.json", sha="file-sha")
    repository.update_file.return_value = {"commit": Mock(sha="new-commit-sha")}

    assert storage.write({"cluster_name": "test"}, "test.example.org", trigger_run=trigger_run) == "new-commit-sha"

    repository.update_file.assert_called_once()
    if trigger_run:
        repository.create_git_ref.assert_called_once_with(ref="refs/tags/apply-new-commit", sha="new-commit-sha")
    else:
        repository.create_git_ref.assert_not_called()


@pytest.mark.parametrize("exists", [True, False])
def test_benchmark_trigger_reuses_existing_tag(exists):
    storage = GithubStorage.__new__(GithubStorage)
    storage.organization = "test-org"
    storage.github = Mock()
    repository = storage.github.get_organization.return_value.get_repo.return_value
    if exists:
        repository.get_git_ref.return_value.object.sha = "0123456789abcdef"
    else:
        repository.get_git_ref.side_effect = GithubException(404, {})
    assert storage.trigger_run("test.example.org", "0123456789abcdef") is not exists
    if exists:
        repository.create_git_ref.assert_not_called()
    else:
        repository.create_git_ref.assert_called_once_with(ref="refs/tags/apply-0123456789", sha="0123456789abcdef")


def test_benchmark_trigger_rejects_a_tag_for_another_commit():
    storage = GithubStorage.__new__(GithubStorage)
    storage.organization = "test-org"
    storage.github = Mock()
    repository = storage.github.get_organization.return_value.get_repo.return_value
    repository.get_git_ref.return_value.object.sha = "another-commit"
    with pytest.raises(GithubStorageException, match="different commit"):
        storage.trigger_run("test.example.org", "0123456789abcdef")
    repository.create_git_ref.assert_not_called()
