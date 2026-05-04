from typing import List, Optional
from mchub.models.magic_castle.terraform_cloud_status import TFCloudStatusCode
from mchub.services.terraform_cloud_api import TerraformCloudVariable


class TerraformCloudMock:
    def destroy_plan(self, workspace_id):
        return "MOCK_RUN_ID"

    def create_project(self, project_name):
        return "MOCK_PROJECT_ID"

    def update_project(self, project_id, agent_pool_name):
        return None

    def create_workspace(self, workspace_name, repo_full_name, project_id):
        return "MOCK_WORKSPACE_ID"

    def set_project_variable_set(
        self, project_id, project_name, variables: List[TerraformCloudVariable]
    ):
        return "MOCK_VARSET_ID"

    def replace_project_variable_set(
        self, project_id, project_name, variables: List[TerraformCloudVariable]
    ):
        return None

    def set_workspace_variable_set(
        self, workspace_id, variables: List[TerraformCloudVariable]
    ):
        return None

    def get_run_apply_log(self, run_id):
        return None

    def get_run_plan_log_json(self, run_id):
        return {"MOCK": "PLAN_LOG"}

    def get_run_status(self, run_id):
        return TFCloudStatusCode.PLANNED, False

    def get_run_by_commit(self, workspace_id, github_sha):
        return "MOCK_RUN_ID"

    def get_tf_state(self, workspace_id) -> Optional[dict]:
        return

    def apply_run(self, run_id):
        return

    def force_execute(self, run_id):
        return

    def add_workspace_tag(self, workspace_id, tag):
        return