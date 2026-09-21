import pytest
from datetime import datetime
from copy import deepcopy
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


@pytest.fixture
def completed_apply():
    return {
        "data": {
            "id": "run-measured", "type": "runs",
            "attributes": {"status": "applied", "is-destroy": False},
            "relationships": {"apply": {"data": {"id": "apply-measured", "type": "applies"}}},
        },
        "included": [{
            "id": "apply-measured", "type": "applies",
            "attributes": {"status": "finished", "status-timestamps": {
                "started-at": "2026-09-20T22:16:34+00:00",
                "finished-at": "2026-09-20T22:17:53+00:00",
            }},
        }],
    }


@pytest.mark.parametrize("offset", ["Z", "+00:00", "-04:00"])
def test_apply_timestamps_use_linked_apply_and_normalize_utc(tf_cloud_client, mock_request, completed_apply, offset):
    hour = "18" if offset == "-04:00" else "22"
    completed_apply["included"][0]["attributes"]["status-timestamps"] = {
        "started-at": f"2026-09-20T{hour}:16:34{offset}",
        "finished-at": f"2026-09-20T{hour}:17:53{offset}",
    }
    unrelated = deepcopy(completed_apply["included"][0])
    unrelated["id"] = "other-apply"
    unrelated["attributes"]["status-timestamps"] = {"started-at": "wrong", "finished-at": "wrong"}
    completed_apply["included"].insert(0, unrelated)
    mock_request.return_value = mock_response(200, completed_apply)
    assert tf_cloud_client.get_apply_timestamps("run-measured") == (
        datetime(2026, 9, 20, 22, 16, 34), datetime(2026, 9, 20, 22, 17, 53),
    )
    mock_request.assert_called_once_with("GET", f"{tf_cloud_client.BASE_URL}/runs/run-measured", params={"include": "apply"})


@pytest.mark.parametrize("timestamps", [
    {}, {"started-at": "2026-09-20T22:16:34Z"},
    {"started-at": "bad", "finished-at": "2026-09-20T22:17:53Z"},
    {"started-at": None, "finished-at": "2026-09-20T22:17:53Z"},
    {"started-at": "2026-09-20T22:18:00Z", "finished-at": "2026-09-20T22:17:53Z"},
    {"started-at": "2026-09-20T22:16:34", "finished-at": "2026-09-20T22:17:53"},
])
def test_apply_timestamps_never_invent_missing_or_invalid_times(tf_cloud_client, mock_request, completed_apply, timestamps):
    completed_apply["included"][0]["attributes"]["status-timestamps"] = timestamps
    mock_request.return_value = mock_response(200, completed_apply)
    assert tf_cloud_client.get_apply_timestamps("run-measured") == (None, None)


@pytest.mark.parametrize("case", ["different_run", "destroy", "applying", "no_apply", "unlinked", "missing", "running"])
def test_apply_timestamps_require_completed_original_deployment(tf_cloud_client, mock_request, completed_apply, case):
    if case == "different_run":
        completed_apply["data"]["id"] = "another-run"
    elif case == "destroy":
        completed_apply["data"]["attributes"]["is-destroy"] = True
    elif case == "applying":
        completed_apply["data"]["attributes"]["status"] = "applying"
    elif case == "no_apply":
        completed_apply["data"]["relationships"]["apply"]["data"] = None
    elif case == "unlinked":
        completed_apply["included"][0]["id"] = "other-apply"
    elif case == "missing":
        completed_apply["included"] = []
    else:
        completed_apply["included"][0]["attributes"]["status"] = "running"
    mock_request.return_value = mock_response(200, completed_apply)
    assert tf_cloud_client.get_apply_timestamps("run-measured") == (None, None)


def test_apply_timestamps_report_api_failure(tf_cloud_client, mock_request):
    mock_request.return_value = mock_response(403)
    with pytest.raises(TerraformCloudException, match="apply timestamps"):
        tf_cloud_client.get_apply_timestamps("run-measured")


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


@pytest.mark.parametrize("previous_destroy", [True, False])
def test_benchmark_commit_creates_a_fresh_deployment_of_verified_configuration(tf_cloud_client, mock_request, previous_destroy):
    mock_request.side_effect = [
        mock_response(200, {"data": [{"id": "old-run", "attributes": {"is-destroy": previous_destroy},
            "relationships": {"configuration-version": {"data": {"id": "cv-matching"}}}}]}),
        mock_response(200, {"data": {"attributes": {"commit-sha": "saved-commit"}}}),
        mock_response(201, {"data": {"id": "new-deployment"}}),
    ]
    assert tf_cloud_client.plan_from_commit("ws-benchmark", "saved-commit") == "new-deployment"
    args, kwargs = mock_request.call_args
    assert args == ("POST", tf_cloud_client.runs_url)
    data = kwargs["json"]["data"]
    assert data["attributes"]["is-destroy"] is False
    assert data["attributes"]["auto-apply"] is False
    assert data["attributes"]["plan-only"] is False
    assert data["relationships"]["configuration-version"]["data"]["id"] == "cv-matching"
    assert data["relationships"]["workspace"]["data"]["id"] == "ws-benchmark"


def test_benchmark_commit_requires_import_when_not_found(tf_cloud_client, mock_request):
    mock_request.return_value = mock_response(200, {"data": []})
    assert tf_cloud_client.plan_from_commit("ws", "new-commit") is None
    mock_request.assert_called_once()


@pytest.mark.parametrize("status,sha", [(200, "wrong-commit"), (403, "saved-commit")])
def test_benchmark_commit_never_plans_an_unverified_configuration(tf_cloud_client, mock_request, status, sha):
    mock_request.side_effect = [
        mock_response(200, {"data": [{"relationships": {"configuration-version": {"data": {"id": "cv-wrong"}}}}]}),
        mock_response(status, {"data": {"attributes": {"commit-sha": sha}}}),
    ]
    with pytest.raises(TerraformCloudException, match="verify"):
        tf_cloud_client.plan_from_commit("ws", "saved-commit")
    assert all(call.args[0] == "GET" for call in mock_request.call_args_list)


@pytest.mark.parametrize(
    ("current_state", "expected"),
    [
        ({"id": "sv-current", "type": "state-versions"}, True),
        (None, False),
    ],
)
def test_workspace_has_state(tf_cloud_client, mock_request, current_state, expected):
    mock_request.return_value = mock_response(
        200,
        json_data={
            "data": {
                "relationships": {
                    "current-state-version": {"data": current_state}
                }
            }
        },
    )

    assert tf_cloud_client.workspace_has_state("ws-123") is expected

    mock_request.assert_called_once_with(
        "GET", f"{tf_cloud_client.BASE_URL}/workspaces/ws-123"
    )


def test_workspace_has_state_api_failure(tf_cloud_client, mock_request):
    mock_request.return_value = mock_response(403, text="Forbidden")

    with pytest.raises(TerraformCloudException, match="Could not inspect workspace state"):
        tf_cloud_client.workspace_has_state("ws-forbidden")


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
    mock_request.return_value = mock_response(201, json_data={"data": {"id": "varset-123"}})

    variables = [
        TerraformCloudVariable("VAR1", "value1", False),
        TerraformCloudVariable("VAR2", "value2", True),
    ]

    tf_cloud_client.set_project_variable_set("project-id-1", "project-name-1", variables)

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
        tf_cloud_client.set_project_variable_set("proj-id", "proj-name", variables)

    assert "Could not set variable set" in str(excinfo.value)


def test_workspace_variable_retry_updates_existing_and_creates_missing(tf_cloud_client, mock_request):
    mock_request.side_effect = [
        mock_response(200, {"data": [{"id": "var-env", "attributes": {"key": "pool", "category": "env"}}], "links": {"next": "page-2"}}),
        mock_response(200, {"data": [{"id": "var-pool", "attributes": {"key": "pool", "category": "terraform"}}]}),
        mock_response(200), mock_response(201),
    ]
    tf_cloud_client.upsert_workspace_variable_set("ws-test", [
        TerraformCloudVariable("pool", "[]", False, hcl=True, category="terraform"),
        TerraformCloudVariable("tfc_eyaml_key", "secret", True, category="terraform"),
    ])
    calls = mock_request.call_args_list
    assert [call.args[0] for call in calls] == ["GET", "GET", "PATCH", "POST"]
    assert calls[1].kwargs["params"]["page[number]"] == 2
    assert calls[2].args[1].endswith("/workspaces/ws-test/vars/var-pool")
    assert calls[2].kwargs["json"]["data"]["attributes"]["value"] == "[]"
    assert calls[3].kwargs["json"]["data"]["attributes"]["key"] == "tfc_eyaml_key"


def test_workspace_variables_are_not_created_when_lookup_fails(tf_cloud_client, mock_request):
    mock_request.return_value = mock_response(503)
    with pytest.raises(TerraformCloudException, match="inspect workspace variables"):
        tf_cloud_client.upsert_workspace_variable_set("ws-test", [TerraformCloudVariable("pool", "[]", False)])
    mock_request.assert_called_once()


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


@pytest.mark.parametrize("state, allowed", [
    ({"resources": []}, True),
    ({"resources": [{"mode": "data", "instances": [{}]}]}, True),
    ({"resources": [{"mode": "managed", "instances": [{}]}]}, False),
    (None, False),
    ({}, False),
])
def test_verify_empty_workspace_checks_managed_instances(tf_cloud_client, mock_request, mocker, state, allowed):
    from mchub.exceptions.invalid_usage_exception import InvalidUsageException
    mock_request.return_value = mock_response(200, {"data": [], "links": {"next": None}})
    mocker.patch.object(tf_cloud_client, "workspace_has_state", return_value=True)
    mocker.patch.object(tf_cloud_client, "get_tf_state", return_value=state)
    if allowed:
        tf_cloud_client.verify_workspace_empty("ws-existing")
    else:
        with pytest.raises(InvalidUsageException):
            tf_cloud_client.verify_workspace_empty("ws-existing")


def test_verify_empty_workspace_rejects_queued_runs_on_later_pages(tf_cloud_client, mock_request):
    from mchub.exceptions.invalid_usage_exception import InvalidUsageException
    mock_request.side_effect = [
        mock_response(200, {"data": [{"attributes": {"status": "applied"}}], "links": {"next": "next-page"}}),
        mock_response(200, {"data": [{"attributes": {"status": "pending"}}]}),
    ]
    with pytest.raises(InvalidUsageException, match="pending Terraform runs"):
        tf_cloud_client.verify_workspace_empty("ws-existing")


def pending_run(run_id, status="planned", discardable=True):
    return {"id": run_id, "attributes": {"status": status, "actions": {"is-discardable": discardable}}}


def test_discard_plans_checks_all_pages_and_waits(tf_cloud_client, mock_request, mocker):
    mocker.patch.object(tf_cloud_client, "workspace_has_state", return_value=False)
    sleep = mocker.patch("mchub.services.terraform_cloud_api.time.sleep")
    mock_request.side_effect = [
        mock_response(200, {"data": [pending_run("new", "pending")], "links": {"next": "older"}}),
        mock_response(200, {"data": [pending_run("old")]}),
        mock_response(202),
        mock_response(200, {"data": pending_run("new", "pending")}),
        mock_response(200, {"data": pending_run("new", "discarded")}),
        mock_response(202),
        mock_response(200, {"data": pending_run("old", "discarded")}),
    ]
    tf_cloud_client.discard_workspace_plans("ws-existing")
    assert [call.args for call in mock_request.call_args_list if call.args[0] == "POST"] == [
        ("POST", f"{tf_cloud_client.runs_url}/new/actions/discard"),
        ("POST", f"{tf_cloud_client.runs_url}/old/actions/discard"),
    ]
    sleep.assert_called_once_with(0.5)


@pytest.mark.parametrize("status", ["planning", "applying", "apply_queued", "confirmed"])
def test_discard_rejects_active_runs_before_mutating_any_plan(tf_cloud_client, mock_request, status):
    from mchub.exceptions.invalid_usage_exception import InvalidUsageException
    mock_request.side_effect = [
        mock_response(200, {"data": [pending_run("plan")], "links": {"next": "older"}}),
        mock_response(200, {"data": [pending_run("active", status, False)]}),
    ]
    with pytest.raises(InvalidUsageException, match="active Terraform runs"):
        tf_cloud_client.discard_workspace_plans("ws-existing")
    assert all(call.args[0] == "GET" for call in mock_request.call_args_list)


@pytest.mark.parametrize("response_code", [403, 409, 500])
def test_discard_failure_stops_deletion(tf_cloud_client, mock_request, mocker, response_code):
    mocker.patch.object(tf_cloud_client, "workspace_has_state", return_value=False)
    mock_request.side_effect = [
        mock_response(200, {"data": [pending_run("plan")]}),
        mock_response(response_code),
    ]
    with pytest.raises(TerraformCloudException, match="Could not discard"):
        tf_cloud_client.discard_workspace_plans("ws-existing")


def test_discard_timeout_is_bounded(tf_cloud_client, mock_request, mocker):
    mocker.patch.object(tf_cloud_client, "workspace_has_state", return_value=False)
    sleep = mocker.patch("mchub.services.terraform_cloud_api.time.sleep")
    mock_request.side_effect = [
        mock_response(200, {"data": [pending_run("plan")]}),
        mock_response(202),
    ] + [mock_response(200, {"data": pending_run("plan")})] * 20
    with pytest.raises(TerraformCloudException, match="still pending"):
        tf_cloud_client.discard_workspace_plans("ws-existing")
    assert sleep.call_count == 19


def test_discard_preserves_plans_when_resources_remain(tf_cloud_client, mock_request, mocker):
    from mchub.exceptions.invalid_usage_exception import InvalidUsageException
    mocker.patch.object(tf_cloud_client, "workspace_has_state", return_value=True)
    mocker.patch.object(tf_cloud_client, "get_tf_state", return_value={
        "resources": [{"mode": "managed", "instances": [{}]}]
    })
    mock_request.return_value = mock_response(200, {"data": [pending_run("plan")]})
    with pytest.raises(InvalidUsageException, match="Tear down all resources"):
        tf_cloud_client.discard_workspace_plans("ws-existing")
    mock_request.assert_called_once_with("GET", f"{tf_cloud_client.BASE_URL}/workspaces/ws-existing/runs")
