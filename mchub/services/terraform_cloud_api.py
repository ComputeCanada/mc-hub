from typing import Optional, List
from dataclasses import dataclass

from mchub.models.magic_castle.terraform_cloud_status import TFCloudStatusCode

from ..configuration import get_config
import requests

from ..exceptions.server_exception import (
    TerraformCloudException,
)


@dataclass
class TerraformCloudVariable:
    name: str
    value: str
    sensitive: bool

    def to_dict(self):
        return {
            "type": "vars",
            "attributes": {
                "key": self.name,
                "value": self.value,
                "description": "",
                "category": "env",
                "hcl": False,
                "sensitive": self.sensitive,
            },
        }


class TerraformCloud:
    BASE_URL = "https://app.terraform.io/api/v2"

    def __init__(self) -> None:
        config = get_config()

        self.organisation_name = config["tfcloud_organization"]
        self.oauth_token_id = config["tfcloud_oauth_vcs_token_id"]

        self.headers = {
            "Authorization": f"Bearer {config['tfcloud_api_token']}",
            "Content-Type": "application/vnd.api+json",
        }

        self.workspace_url = (
            f"{self.BASE_URL}/organizations/{self.organisation_name}/workspaces"
        )

        self.runs_url = f"{self.BASE_URL}/runs"

    def _request(self, method, url, **kwargs):
        return requests.request(method, url, headers=self.headers, **kwargs)

    def destroy_plan(self, workspace_id):
        destroy_payload = {
            "data": {
                "attributes": {"message": "Plan destroy", "is-destroy": True},
                "type": "runs",
                "relationships": {
                    "workspace": {
                        "data": {"type": "workspaces", "id": f"{workspace_id}"}
                    },
                },
            }
        }

        response = self._request("POST", self.runs_url, json=destroy_payload)

        try:
            run_id = response.json()["data"]["id"]
        except Exception:
            raise TerraformCloudException(
                "Could not destroy workspace",
                additional_details=f"{workspace_id=}, error: {response.text}",
            )
        return run_id

    def get_agent_pool_id(self, agent_pool_name: str) -> str:
        url = f"{self.BASE_URL}/organizations/{self.organisation_name}/agent-pools"
        response = self._request("GET", url, params={"filter[name]": agent_pool_name})
        try:
            return response.json()["data"][0]["id"]
        except Exception:
            raise TerraformCloudException(
                "Could not find agent pool",
                additional_details=f"{agent_pool_name=}, error: {response.text}",
            )

    def create_project(self, project_name, agent_pool_name: Optional[str] = None):
        url = f"{self.BASE_URL}/organizations/{self.organisation_name}/projects"

        attributes = {
            "name": project_name,
            "description": f"MCHub project: {project_name}",
        }
        relationships = {
            "organization": {
                "data": {"id": self.organisation_name, "type": "organizations"}
            }
        }

        if agent_pool_name:
            agent_pool_id = self.get_agent_pool_id(agent_pool_name)
            attributes["default-execution-mode"] = "agent"
            relationships["default-agent-pool"] = {"data": {"type": "agent-pools", "id": agent_pool_id}}
        else:
            attributes["default-execution-mode"] = "default"

        payload = {
            "data": {
                "attributes": attributes,
                "type": "projects",
                "relationships": relationships,
            }
        }
        response = self._request("POST", url, json=payload)

        try:
            project_id = response.json()["data"]["id"]
        except Exception:
            raise TerraformCloudException(
                "Could not create workspace",
                additional_details=f"{project_name=}, error: {response.text}",
            )
        return project_id

    def create_workspace(self, workspace_name, repo_full_name, project_id):
        workspace_payload = {
            "data": {
                "type": "workspaces",
                "attributes": {
                    "name": workspace_name,
                    "auto-apply": "false",
                    "auto-apply-run-trigger": "false",
                    "file-triggers-enabled": "false",
                    "queue-all-runs": "true",
                    "vcs-repo": {
                        "tags-regex": r"^apply-[a-f0-9]+$",
                        "identifier": repo_full_name,
                        "oauth-token-id": self.oauth_token_id,
                        "branch": "main",
                        "default-branch": True,
                    },
                },
                "relationships": {
                    "project": {"data": {"type": "projects", "id": project_id}}
                },
            }
        }

        response = self._request("POST", self.workspace_url, json=workspace_payload)

        try:
            workspace_id = response.json()["data"]["id"]
        except Exception:
            # TODO No error in UI (show Not Found)
            raise TerraformCloudException(
                "Could not create workspace",
                additional_details=f"{workspace_name=}, error: {response.text}",
            )
        return workspace_id

    def set_project_variable_set(
        self, project_id, project_name, variables: List[TerraformCloudVariable]
    ):
        url = f"{self.BASE_URL}/organizations/{self.organisation_name}/varsets"
        payload = {
            "data": {
                "type": "varsets",
                "attributes": {
                    "name": f"{project_name}",
                    "description": f"variable set used for project={project_name}",
                    "global": False,
                    "priority": False,
                },
                "relationships": {
                    "organization": {
                        "data": {"type": "organizations", "id": self.organisation_name}
                    },
                    "parent": {"data": {"id": project_id, "type": "projects"}},
                    "projects": {"data": [{"id": project_id, "type": "projects"}]},
                    "vars": {"data": [var.to_dict() for var in variables]},
                },
            }
        }

        res = self._request("POST", url, json=payload)
        if res.status_code != 201:
            raise TerraformCloudException(
                "Could not set variable set",
                additional_details=f"{self.organisation_name=}, {project_name=} vars={[v.name for v in variables]}, error: {res.text}",
            )

    def set_workspace_variable_set(
        self, workspace_id, variables: List[TerraformCloudVariable]
    ):
        url = f"{self.BASE_URL}/vars"
        for variable in variables:
            payload = {
                "data": {
                    "type": "vars",
                    "attributes": {
                        "key": variable.name,
                        "value": variable.value,
                        "description": "",
                        "category": "env",
                        "hcl": False,
                        "sensitive": variable.sensitive,
                    },
                    "relationships": {
                        "workspace": {
                            "data": {"id": workspace_id, "type": "workspaces"}
                        }
                    },
                }
            }

            res = self._request("POST", url, json=payload)
            if res.status_code != 201:
                raise TerraformCloudException(
                    "Could not set workspace variable set",
                    additional_details=f"{workspace_id=}, variable={variable.name}, error: {res.text}",
                )

    def get_run_status(self, run_id):
        url = f"{self.BASE_URL}/runs/{run_id}"
        res = self._request("GET", url)
        if res.status_code == 200:
            try:
                status = res.json()["data"]["attributes"]["status"]
                is_destroy = res.json()["data"]["attributes"]["is-destroy"]
                return TFCloudStatusCode(status), is_destroy
            except IndexError:
                return None, None
            except TypeError:
                return None, None

        else:
            raise TerraformCloudException(
                "Could not find trigger run",
                additional_details=f"{run_id=}, error: {res.text}",
            )

    def get_run_by_commit(self, workspace_id, github_sha):
        url = f"{self.BASE_URL}/workspaces/{workspace_id}/runs"
        params = {
            "page[size]": 1,  # Limit to the most recent run
        }
        params["search[commit]"] = github_sha

        res = self._request("GET", url, params=params)
        if res.status_code == 200:
            try:
                run_id = res.json()["data"][0]["id"]
                return run_id
            except IndexError:
                # No run found
                return None

        else:
            raise TerraformCloudException(
                "Could not find trigger run",
                additional_details=f"{workspace_id=}, error: {res.text}",
            )

    def get_run_apply_log(self, run_id) -> str:
        url = f"{self.BASE_URL}/runs/{run_id}/apply"
        res = self._request("GET", url)
        if res.status_code == 200:
            try:
                return res.json()["data"]["attributes"]["log-read-url"]

            except KeyError:
                raise TerraformCloudException(
                    "Could not find log url",
                    additional_details=f"{run_id=}, error: {res.text}",
                )

        else:
            raise TerraformCloudException(
                "Could not find apply run log",
                additional_details=f"{run_id=}, error: {res.text}",
            )

    def get_run_plan_log_json(self, run_id) -> Optional[dict]:
        url = f"{self.BASE_URL}/runs/{run_id}/plan"
        res = self._request("GET", url)
        if res.status_code == 200:
            if res.json()["data"]["attributes"]["status"] == "errored":
                raise TerraformCloudException(
                    "Plan return error",
                    additional_details=f"{run_id=}, error: {res.text}",
                )

            try:
                is_finished = res.json()["data"]["attributes"]["status"] == "finished"
                plan_id = res.json()["data"]["id"]

                if is_finished:
                    log_url = f"{self.BASE_URL}/plans/{plan_id}/json-output"
                    return self._request("GET", log_url).json()
                else:
                    return None
            except IndexError:
                raise TerraformCloudException(
                    "Could not find plan id",
                    additional_details=f"{run_id=}, error: {res.text}",
                )

        else:
            raise TerraformCloudException(
                "Could not find apply log",
                additional_details=f"{run_id=}, error: {res.text}",
            )

    def get_tf_state(self, workspace_id) -> Optional[dict]:
        url = f"{self.BASE_URL}/workspaces/{workspace_id}/current-state-version"
        res = self._request("GET", url)
        if res.status_code == 200:
            try:
                is_finished = res.json()["data"]["attributes"]["status"] == "finalized"

                if is_finished:
                    state_url = res.json()["data"]["attributes"][
                        "hosted-state-download-url"
                    ]
                    return self._request("GET", state_url).json()
                else:
                    return None
            except IndexError:
                raise TerraformCloudException(
                    "Could not find tf state",
                    additional_details=f"{workspace_id=}, error: {res.text}",
                )

        else:
            raise TerraformCloudException(
                "Invalid workspace to retrive state",
                additional_details=f"{workspace_id=}, error: {res.text}",
            )

    def apply_run(self, run_id):
        url = f"{self.BASE_URL}/runs/{run_id}/actions/apply"
        res = self._request("POST", url)
        if res.status_code != 202:
            raise TerraformCloudException(
                "Could not apply run",
                additional_details=f"{run_id=}, error: {res.text}",
            )

    def add_workspace_tag(self, workspace_id, tag):
        url = f"{self.BASE_URL}/workspaces/{workspace_id}/relationships/tags"
        payload = {"data": [{"type": "tags", "attributes": {"name": tag}}]}
        res = self._request("POST", url, json=payload)
        if res.status_code != 204:
            raise TerraformCloudException(
                "Could not add tag to workspace",
                additional_details=f"{workspace_id=}, {tag=}, error: {res.text}",
            )

    def force_execute(self, run_id):
        url = f"{self.BASE_URL}/runs/{run_id}/actions/force-execute"
        res = self._request("POST", url)
        match res.status_code:
            case 202 | 403:  # 403 is the case where the run is not in pending state
                return
            case _:
                raise TerraformCloudException(
                    "Invalid Error for force_execute",
                    additional_details=f"{run_id=}, error: {res.text}",
                )


_terraform_cloud_instance = None


def get_terraform_cloud() -> TerraformCloud:
    global _terraform_cloud_instance
    if _terraform_cloud_instance is None:
        _terraform_cloud_instance = TerraformCloud()
    return _terraform_cloud_instance