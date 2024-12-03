from ..configuration import get_config

from github import Github
from github import Auth
from github import GithubException
import time
import json


import time
from contextlib import contextmanager
import random


@contextmanager
def retry(max_retry=5, sleep_s=5):
    """
    A context manager that retries the execution of the enclosed code block
    upon catching an exception.
    Useful to retry repo creation

    Args:
        max_retry (int): The maximum number of attempts (including the first one).
        sleep_s (int): The number of seconds to sleep between retries.
    """
    # max_retry is 1-indexed (e.g., 5 attempts). range is 0-indexed.
    for attempt in range(max_retry):
        try:
            # The 'yield' pauses execution and runs the code block inside the 'with' statement.
            yield
            # If the code block finishes without raising an exception, we break the retry loop.
            break

        except Exception as e:
            if attempt == max_retry - 1:
                # If this was the final attempt, re-raise the exception to the user.
                print(
                    f"--- Final attempt ({attempt + 1}/{max_retry}) failed. Raising exception. ---"
                )
                raise

            # If it's not the final attempt, print a message and prepare for the next retry.
            print(
                f"Attempt {attempt + 1}/{max_retry} failed with error: {type(e).__name__}: {e}"
            )
            print(f"Retrying in {sleep_s} seconds...")
            time.sleep(sleep_s)


class GithubStorage:
    def __init__(self):
        config = get_config()
        self.organization = config["github_organization"]

        auth = Auth.Token(config["github_token"])
        self.github = Github(auth=auth)

    def _get_repo_name(self, hostname):
        import hashlib

        hash_object = hashlib.sha256(hostname.encode())
        hashed_name = hash_object.hexdigest()[:10]
        repo_name = f"mchub-{hashed_name}"
        return repo_name

    @staticmethod
    def _retry(func, max_retry=5, sleep_s=5):
        for _ in range(max_retry):
            try:
                time.sleep(sleep_s)
                return func()
            except Exception as e:
                raise e

    def create_repo(self, hostname, template_name):
        org = self.github.get_organization(self.organization)
        self.template_repo = org.get_repo(template_name)

        repo_name = self._get_repo_name(hostname)

        repo_description = f"mchub repo for unique_name '{hostname}'"

        org = self.github.get_organization(self.organization)

        repo = org.create_repo_from_template(
            name=repo_name,
            repo=self.template_repo,
            description=repo_description,
            private=True,
        )

        # Wait for the repo to apply the commits from the template.
        # Otherwise, we might have a issue with commit order.
        commits = repo.get_commits()
        nb_commits = 0
        while nb_commits < 1:
            try:
                nb_commits = commits.totalCount
            except GithubException as e:
                # Skip for no commit error
                if e.status != 409:
                    raise e

            time.sleep(1)

        return f"{self.organization}/{repo_name}"

    def write(self, tf_data, hostname, filename="terraform.tfvars.json"):
        # Check if the file exists in the repository
        repo_name = self._get_repo_name(hostname)
        org = self.github.get_organization(self.organization)
        repo = org.get_repo(repo_name)

        tf_str = json.dumps(tf_data)

        try:
            file = repo.get_contents(filename)
            # Update the file if it exists
            commit = repo.update_file(
                path=file.path,
                message=f"Update {filename} content",
                content=tf_str,
                sha=file.sha,  # Required for updating
            )
        except Exception as err:
            # Create the file if it does not exist
            commit = repo.create_file(
                path=filename,
                message=f"Add initial {filename}",
                content=tf_str,
            )

        sha = commit["commit"].sha
        repo.create_git_ref(ref=f"refs/tags/apply-{sha[:10]}", sha=sha)
        return sha


_github_storage_instance = None


def get_github_storage() -> GithubStorage:
    global _github_storage_instance
    if _github_storage_instance is None:
        _github_storage_instance = GithubStorage()
    return _github_storage_instance