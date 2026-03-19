import pytest
from unittest.mock import patch, Mock
import requests

from mchub.services.terraform_cloud_api import (
    TerraformCloud,
    TerraformCloudVariable,
    TerraformCloudException,
    TFCloudStatusCode,
)


@pytest.fixture(autouse=True)
def mock_get_config():
    with patch("mchub.services.terraform_cloud_api.get_config") as mock_config:
        mock_config.return_value = {
            "tfcloud_organization": "test-org",
            "tfcloud_oauth_vcs_token_id": "oauth-12345",
            "tfcloud_api_token": "api-token-xyz",
        }
        yield mock_config


@pytest.fixture
def tf_cloud_client():
    return TerraformCloud()


@pytest.fixture
def mock_request(tf_cloud_client):
    with patch.object(tf_cloud_client, "_request") as mock_req:
        yield mock_req


# Helper to create a standard mock response object
def mock_response(status_code, json_data=None, text=""):
    mock = Mock(spec=requests.Response)
    mock.status_code = status_code
    mock.text = text
    if json_data is not None:
        mock.json.return_value = json_data
    else:
        # Avoid unexpected calls to .json() if not needed
        mock.json.side_effect = AttributeError("json() not available")
    return mock


def test_terraform_cloud_variable_to_dict():
    """Tests the to_dict method of the TerraformCloudVariable dataclass."""
    variable = TerraformCloudVariable(name="MY_VAR", value="secret", sensitive=True)

    expected_dict = {
        "type": "vars",
        "attributes": {
            "key": "MY_VAR",
            "value": "secret",
            "description": "",
            "category": "env",
            "hcl": False,
            "sensitive": True,
        },
    }

    assert variable.to_dict() == expected_dict


def test_terraform_cloud_init(tf_cloud_client):
    """Tests that the client is initialized correctly with configuration."""
    assert tf_cloud_client.organisation_name == "test-org"
    assert tf_cloud_client.oauth_token_id == "oauth-12345"
    assert tf_cloud_client.BASE_URL == "https://app.terraform.io/api/v2"
    assert tf_cloud_client.headers["Authorization"] == "Bearer api-token-xyz"


def test_destroy_plan_success(tf_cloud_client, mock_request):
    """Tests successful run creation for workspace destruction."""
    mock_request.return_value = mock_response(
        201, json_data={"data": {"id": "run-destroy-123"}}
    )

    workspace_id = "ws-123"
    run_id = tf_cloud_client.destroy_plan(workspace_id)

    assert run_id == "run-destroy-123"

    # Verify the request was made correctly
    mock_request.assert_called_once()
    args, kwargs = mock_request.call_args
    assert args[0] == "POST"
    assert args[1] == tf_cloud_client.runs_url
    assert kwargs["json"]["data"]["attributes"]["is-destroy"] is True
    assert (
        kwargs["json"]["data"]["relationships"]["workspace"]["data"]["id"]
        == workspace_id
    )


def test_destroy_plan_failure(tf_cloud_client, mock_request):
    """Tests exception handling when destroy_plan API call fails."""
    mock_request.return_value = mock_response(400, text="Bad Request details")

    with pytest.raises(TerraformCloudException) as excinfo:
        tf_cloud_client.destroy_plan("ws-fail")

    assert "Could not destroy workspace" in str(excinfo.value)


def test_create_project_success(tf_cloud_client, mock_request):
    """Tests successful project creation."""
    mock_request.return_value = mock_response(
        201, json_data={"data": {"id": "project-123"}}
    )

    project_id = tf_cloud_client.create_project("test-project")

    assert project_id == "project-123"

    # Verify request payload
    args, kwargs = mock_request.call_args
    assert args[0] == "POST"
    assert "projects" in args[1]  # Check URL
    assert kwargs["json"]["data"]["attributes"]["name"] == "test-project"


def test_create_project_failure(tf_cloud_client, mock_request):
    """Tests exception handling when create_project API call fails."""
    mock_request.return_value = mock_response(409, text="Conflict, project exists")

    with pytest.raises(TerraformCloudException) as excinfo:
        tf_cloud_client.create_project("existing-project")

    assert "Could not create workspace" in str(excinfo.value)


def test_create_workspace_success(tf_cloud_client, mock_request):
    """Tests successful workspace creation."""
    mock_request.return_value = mock_response(
        201, json_data={"data": {"id": "ws-new-456"}}
    )

    workspace_id = tf_cloud_client.create_workspace(
        "new-ws", "owner/repo", "project-123"
    )

    assert workspace_id == "ws-new-456"

    # Verify request payload details
    args, kwargs = mock_request.call_args
    payload = kwargs["json"]["data"]
    assert payload["attributes"]["name"] == "new-ws"
    assert payload["attributes"]["vcs-repo"]["identifier"] == "owner/repo"
    assert payload["relationships"]["project"]["data"]["id"] == "project-123"


def test_create_workspace_failure(tf_cloud_client, mock_request):
    """Tests exception handling when create_workspace API call fails."""
    mock_request.return_value = mock_response(400, text="Invalid workspace name")

    with pytest.raises(TerraformCloudException) as excinfo:
        tf_cloud_client.create_workspace("bad-name", "owner/repo", "project-123")

    assert "Could not create workspace" in str(excinfo.value)


def test_set_variable_set_success(tf_cloud_client, mock_request):
    """Tests successful creation of a variable set."""
    mock_request.return_value = mock_response(201)

    variables = [
        TerraformCloudVariable("VAR1", "value1", False),
        TerraformCloudVariable("VAR2", "value2", True),
    ]

    tf_cloud_client.set_variable_set("project-id-1", "project-name-1", variables)

    mock_request.assert_called_once()

    # Verify the vars data structure within the payload
    args, kwargs = mock_request.call_args
    vars_data = kwargs["json"]["data"]["relationships"]["vars"]["data"]
    assert len(vars_data) == 2
    assert vars_data[0]["attributes"]["key"] == "VAR1"
    assert vars_data[1]["attributes"]["sensitive"] is True


def test_set_variable_set_failure(tf_cloud_client, mock_request):
    """Tests exception handling when set_variable_set API call fails."""
    mock_request.return_value = mock_response(422, text="Validation Failed")

    variables = [TerraformCloudVariable("VAR1", "value1", False)]

    with pytest.raises(TerraformCloudException) as excinfo:
        tf_cloud_client.set_variable_set("proj-id", "proj-name", variables)

    assert "Could not set variable set" in str(excinfo.value)


def test_get_run_status_success(tf_cloud_client, mock_request):
    """Tests successful retrieval of run status and destroy flag."""
    mock_request.return_value = mock_response(
        200,
        json_data={"data": {"attributes": {"status": "applied", "is-destroy": False}}},
    )

    status, is_destroy = tf_cloud_client.get_run_status("run-456")

    # Assuming TFCloudStatusCode is an Enum that maps 'applied'
    assert status == TFCloudStatusCode("applied")
    assert is_destroy is False


def test_get_run_status_not_found(tf_cloud_client, mock_request):
    """Tests when run data is not found (IndexError for JSON path)."""
    # Mocking a response that returns an empty or unexpected JSON structure
    mock_request.return_value = mock_response(200, json_data={"data": []})

    status, is_destroy = tf_cloud_client.get_run_status("run-not-found")

    assert status is None
    assert is_destroy is None


def test_get_run_status_api_failure(tf_cloud_client, mock_request):
    """Tests exception handling when get_run_status API call fails."""
    mock_request.return_value = mock_response(404, text="Run not found via API")

    with pytest.raises(TerraformCloudException) as excinfo:
        tf_cloud_client.get_run_status("run-fail")

    assert "Could not find trigger run" in str(excinfo.value)


def test_get_run_by_commit_success(tf_cloud_client, mock_request):
    """Tests successful retrieval of run ID based on commit SHA."""
    mock_request.return_value = mock_response(
        200,
        json_data={
            "data": [
                {"id": "run-sha-match"},
                {"id": "run-older"},  # Should only return the first one
            ]
        },
    )

    run_id = tf_cloud_client.get_run_by_commit("ws-101", "abcdef012345")

    assert run_id == "run-sha-match"

    # Verify the request parameters
    args, kwargs = mock_request.call_args
    assert kwargs["params"]["search[commit]"] == "abcdef012345"


def test_get_run_by_commit_no_run(tf_cloud_client, mock_request):
    """Tests when no run is found for the given commit (IndexError for JSON path)."""
    mock_request.return_value = mock_response(200, json_data={"data": []})

    run_id = tf_cloud_client.get_run_by_commit("ws-101", "no-match-sha")

    assert run_id is None


def test_get_run_by_commit_api_failure(tf_cloud_client, mock_request):
    """Tests exception handling when get_run_by_commit API call fails."""
    mock_request.return_value = mock_response(500, text="Internal Server Error")

    with pytest.raises(TerraformCloudException) as excinfo:
        tf_cloud_client.get_run_by_commit("ws-fail", "sha")

    assert "Could not find trigger run" in str(excinfo.value)


def test_get_run_apply_log_success(tf_cloud_client, mock_request):
    """Tests successful retrieval of the apply log URL."""
    expected_url = "https://log-storage.com/apply-log-123"
    mock_request.return_value = mock_response(
        200, json_data={"data": {"attributes": {"log-read-url": expected_url}}}
    )

    log_url = tf_cloud_client.get_run_apply_log("run-apply-123")

    assert log_url == expected_url


def test_get_run_apply_log_json_error(tf_cloud_client, mock_request):
    """Tests exception handling when log URL cannot be parsed from JSON."""
    mock_request.return_value = mock_response(
        200,
        json_data={"data": {}},  # Missing 'attributes'
    )

    with pytest.raises(TerraformCloudException) as excinfo:
        tf_cloud_client.get_run_apply_log("run-bad-json")

    assert "Could not find log url" in str(excinfo.value)


def test_get_run_plan_log_json_finished_success(tf_cloud_client, mock_request):
    """Tests successful retrieval of the plan JSON when plan is finished."""
    # First call to get plan status and ID
    mock_request.side_effect = [
        mock_response(
            200,
            json_data={
                "data": {"id": "plan-123", "attributes": {"status": "finished"}}
            },
        ),
        # Second call to get the JSON output
        mock_response(200, json_data={"plan_output": "resources"}),
    ]

    plan_json = tf_cloud_client.get_run_plan_log_json("run-plan-123")

    assert plan_json == {"plan_output": "resources"}


def test_get_run_plan_log_json_not_finished(tf_cloud_client, mock_request):
    """Tests that None is returned when the plan is not finished."""
    mock_request.return_value = mock_response(
        200, json_data={"data": {"id": "plan-123", "attributes": {"status": "pending"}}}
    )

    plan_json = tf_cloud_client.get_run_plan_log_json("run-pending-123")

    assert plan_json is None
    mock_request.assert_called_once()  # Only the first request should run


def test_get_tf_state_finalized_success(tf_cloud_client, mock_request):
    """Tests successful retrieval of the state JSON when state is finalized."""
    state_download_url = "https://state-storage.com/state-123.json"

    # First call to get state version info
    mock_request.side_effect = [
        mock_response(
            200,
            json_data={
                "data": {
                    "attributes": {
                        "status": "finalized",
                        "hosted-state-download-url": state_download_url,
                    }
                }
            },
        ),
        # Second call to download the state file
        mock_response(200, json_data={"state_version": 4}),
    ]

    tf_state = tf_cloud_client.get_tf_state("ws-state-123")

    assert tf_state == {"state_version": 4}


def test_get_tf_state_not_finalized(tf_cloud_client, mock_request):
    """Tests that None is returned when the state is not finalized."""
    mock_request.return_value = mock_response(
        200,
        json_data={
            "data": {
                "attributes": {"status": "pending", "hosted-state-download-url": "url"}
            }
        },
    )

    tf_state = tf_cloud_client.get_tf_state("ws-pending-123")

    assert tf_state is None
    mock_request.assert_called_once()  # Only the first request should run


def test_apply_run_success(tf_cloud_client, mock_request):
    """Tests successful application of a run."""
    mock_request.return_value = mock_response(202)  # Accepted

    tf_cloud_client.apply_run("run-to-apply")

    mock_request.assert_called_once()
    args, _ = mock_request.call_args
    assert args[0] == "POST"
    assert "actions/apply" in args[1]


def test_apply_run_failure(tf_cloud_client, mock_request):
    """Tests exception handling when apply_run API call fails."""
    mock_request.return_value = mock_response(409, text="Run already applied")

    with pytest.raises(TerraformCloudException) as excinfo:
        tf_cloud_client.apply_run("run-fail-apply")

    assert "Could not apply run" in str(excinfo.value)


def test_force_execute_success_202(tf_cloud_client, mock_request):
    """Tests successful force execution (status code 202)."""
    mock_request.return_value = mock_response(202)  # Accepted

    # Should not raise an exception
    tf_cloud_client.force_execute("run-force-1")

    mock_request.assert_called_once()
    args, _ = mock_request.call_args
    assert args[0] == "POST"
    assert "actions/force-execute" in args[1]


def test_force_execute_success_403(tf_cloud_client, mock_request):
    """Tests successful force execution (status code 403, indicating run not in pending state)."""
    mock_request.return_value = mock_response(403)  # Forbidden/Not applicable

    # Should not raise an exception as per the match/case logic
    tf_cloud_client.force_execute("run-force-2")

    mock_request.assert_called_once()


def test_force_execute_failure(tf_cloud_client, mock_request):
    """Tests exception handling when force_execute API call fails with an unexpected status code."""
    mock_request.return_value = mock_response(404, text="Run not found")

    with pytest.raises(TerraformCloudException) as excinfo:
        tf_cloud_client.force_execute("run-fail-force")

    assert "Invalid Error for force_execute" in str(excinfo.value)