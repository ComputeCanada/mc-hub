import json
from unittest.mock import Mock

import pytest
import requests

from mchub.database import db
from mchub.models.magic_castle.magic_castle import MagicCastleORM
from tests.test_helpers import app, client, generate_test_clusters, mock_clusters_path  # noqa: F401
from tests.mocks.configuration.config_mock import config_auth_saml_mock as config_mock  # noqa: F401

PREFIX = "/api/tfcloud-proxy/"
HEADERS = {"Authorization": "Bearer cluster-token"}
WORKSPACE = "ws-owned"
POOL = {"id": "var-pool", "type": "vars", "attributes": {"key": "pool", "category": "terraform", "value": '["node1"]'}}


def response(body, status=200):
    return Mock(status_code=status, content=json.dumps(body).encode(), json=Mock(return_value=body))


@pytest.fixture
def upstream(app, mocker):
    cluster = db.session.scalars(db.select(MagicCastleORM)).first()
    cluster.cluster_token = "cluster-token"
    cluster.tfcloud_workspace = WORKSPACE
    db.session.commit()
    mocker.patch("mchub.resources.tfcloud_proxy.get_terraform_cloud", return_value=Mock(
        BASE_URL="https://app.terraform.io/api/v2", headers={"Authorization": "Bearer operator-token"}))
    return mocker.patch("mchub.resources.tfcloud_proxy.requests.request")


def patch_payload(value='["node2"]', variable_id="var-pool"):
    return {"data": {"id": variable_id, "type": "vars", "attributes": {"value": value, "hcl": True, "category": "terraform"}}}


def run_payload():
    return {"data": {"type": "runs", "attributes": {
        "message": "Slurm resume node2", "target-addrs": [], "auto-apply": True,
        "variables": [{"key": "pool", "value": '["node1", "node2"]'}],
    }, "relationships": {"workspace": {"data": {"type": "workspaces", "id": WORKSPACE}}}}}


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer unknown"}, {"Authorization": "Basic cluster-token"}])
def test_requires_cluster_token(client, upstream, headers):
    assert client.get(PREFIX + f"workspaces/{WORKSPACE}", headers=headers).status_code == 401
    upstream.assert_not_called()


@pytest.mark.parametrize("method,path", [
    ("GET", "organizations/org/workspaces"), ("GET", "projects/prj-other"),
    ("GET", "state-versions/sv-other"), ("GET", "workspaces/ws-other"),
    ("GET", "workspaces/ws-other/vars"), ("PATCH", "workspaces/ws-owned"),
    ("POST", "workspaces/ws-owned/actions/unlock"), ("POST", "runs/run-other/actions/apply"),
    ("POST", "runs/run-other/actions/cancel"), ("GET", "workspaces/ws-owned/current-state-version"),
    ("GET", "workspaces/ws-owned/../ws-other"), ("GET", "workspaces/ws-owned/%2e%2e/ws-other"),
    ("GET", "workspaces/ws-owned%252f..%252fws-other"), ("GET", "workspaces/ws-owned/"),
    ("GET", "workspaces/ws-owned/resources/var-pool"), ("HEAD", "workspaces/ws-owned"),
])
def test_denies_unlisted_routes_without_forwarding(client, upstream, method, path):
    assert client.open(PREFIX + path, method=method, headers=HEADERS).status_code == 403
    upstream.assert_not_called()


@pytest.mark.parametrize("query", ["include=organization", "page[number]=1&page[number]=2", "page[number]=-1", "filter[workspace]=ws-other"])
def test_denies_query_bypasses(client, upstream, query):
    assert client.get(PREFIX + f"workspaces/{WORKSPACE}/resources?{query}", headers=HEADERS).status_code == 403
    upstream.assert_not_called()


def test_workspace_and_resource_pagination(client, upstream):
    for suffix, params in [("", {}), ("/resources?page[number]=2&page[size]=100", {"page[number]": "2", "page[size]": "100"})]:
        body = {"data": [], "links": {"next": None}}
        upstream.return_value = response(body)
        result = client.get(PREFIX + f"workspaces/{WORKSPACE}" + suffix, headers=HEADERS)
        assert result.status_code == 200
        assert result.json == body
        assert upstream.call_args.kwargs["params"] == params
        assert upstream.call_args.kwargs["headers"]["Authorization"] == "Bearer operator-token"
        assert upstream.call_args.kwargs["allow_redirects"] is False


def test_only_pool_is_returned_across_variable_pages(client, upstream):
    secret = {"id": "var-secret", "attributes": {"key": "secret", "category": "terraform", "value": "hidden"}}
    upstream.side_effect = [response({"data": [secret], "links": {"next": "https://untrusted.example/path"}}),
                            response({"data": [POOL], "links": {"next": None}})]
    result = client.get(PREFIX + f"workspaces/{WORKSPACE}/vars", headers=HEADERS)
    assert result.json == {"data": [POOL], "links": {"next": None}}
    assert upstream.call_args.kwargs["url"] == f"https://app.terraform.io/api/v2/workspaces/{WORKSPACE}/vars"
    assert upstream.call_args.kwargs["params"]["page[number]"] == 2


@pytest.mark.parametrize("variable_id", ["var-otherworkspace", "var-secret"])
def test_variable_id_must_be_owned_pool(client, upstream, variable_id):
    upstream.return_value = response({"data": [POOL, {"id": "var-secret", "attributes": {"key": "secret", "category": "terraform"}}]})
    result = client.patch(PREFIX + f"workspaces/{WORKSPACE}/vars/{variable_id}", headers=HEADERS, json=patch_payload(variable_id=variable_id))
    assert result.status_code == 403
    assert [c.kwargs["method"] for c in upstream.call_args_list] == ["GET"]


def test_pool_update_preserves_client_payload(client, upstream):
    upstream.side_effect = [response({"data": [POOL]}), response({"data": POOL})]
    payload = patch_payload()
    result = client.patch(PREFIX + f"workspaces/{WORKSPACE}/vars/var-pool", headers=HEADERS, json=payload)
    assert result.status_code == 200
    assert upstream.call_args.kwargs["json"] == payload
    assert upstream.call_args.kwargs["method"] == "PATCH"


@pytest.mark.parametrize("value", ['file("/secret")', '["${file(\"/secret\")}"]', '["%{ if true }x%{ endif }"]', '{}', '[1]', None])
def test_pool_rejects_non_host_arrays(client, upstream, value):
    result = client.patch(PREFIX + f"workspaces/{WORKSPACE}/vars/var-pool", headers=HEADERS, json=patch_payload(value))
    assert result.status_code == 403
    upstream.assert_not_called()


@pytest.mark.parametrize("change", ["workspace", "missing-workspace", "destroy", "configuration", "variable", "extra", "null"])
def test_run_payload_bypasses_are_denied(client, upstream, change):
    payload = run_payload()
    if change == "workspace":
        payload["data"]["relationships"]["workspace"]["data"]["id"] = "ws-other"
    elif change == "missing-workspace":
        payload["data"]["relationships"] = {}
    elif change == "destroy":
        payload["data"]["attributes"]["is-destroy"] = True
    elif change == "configuration":
        payload["data"]["relationships"]["configuration-version"] = {"data": {"id": "cv-other"}}
    elif change == "variable":
        payload["data"]["attributes"]["variables"][0]["key"] = "credentials"
    elif change == "extra":
        payload["included"] = []
    else:
        payload = []
    assert client.post(PREFIX + "runs", headers=HEADERS, json=payload).status_code == 403
    upstream.assert_not_called()


@pytest.mark.parametrize("targets", [[], ['module.cluster.openstack_compute_instance_v2.nodes["node1"]', 'module.cluster.module.provision.terraform_data.wait']])
def test_autoscaling_run_preserves_targets_and_auto_apply(client, upstream, targets):
    payload = run_payload()
    payload["data"]["attributes"]["target-addrs"] = targets
    upstream.return_value = response({"data": {"id": "run-owned"}}, 201)
    assert client.post(PREFIX + "runs", headers=HEADERS, json=payload).status_code == 201
    assert upstream.call_args.kwargs["json"] == payload


@pytest.mark.parametrize("workspace,status", [(WORKSPACE, 200), ("ws-other", 403), (None, 403)])
def test_run_status_checks_ownership_before_disclosing_response(client, upstream, workspace, status):
    body = {"data": {"attributes": {"status": "applied"}, "relationships": {"workspace": {"data": {"id": workspace}}}}}
    upstream.return_value = response(body)
    result = client.get(PREFIX + "runs/run-example", headers=HEADERS)
    assert result.status_code == status
    if status == 200:
        assert result.json == body
    else:
        assert "applied" not in result.text


@pytest.mark.parametrize("status", [302, 403, 500])
def test_upstream_errors_and_redirects_do_not_disclose_body(client, upstream, status):
    upstream.return_value = response({"secret": "do-not-disclose"}, status)
    result = client.get(PREFIX + f"workspaces/{WORKSPACE}", headers=HEADERS)
    assert result.status_code == (403 if status == 403 else 502)
    assert "do-not-disclose" not in result.text
    assert upstream.call_count == 1


def test_lookup_network_failure_cannot_authorize_write(client, upstream):
    upstream.side_effect = requests.Timeout("sensitive details")
    result = client.patch(PREFIX + f"workspaces/{WORKSPACE}/vars/var-pool", headers=HEADERS, json=patch_payload())
    assert result.status_code == 502
    assert "sensitive details" not in result.text
    assert upstream.call_count == 1


def test_operator_configured_pool(client, upstream, mocker):
    mocker.patch("mchub.resources.tfcloud_proxy.get_config", return_value={"tfcloud_autoscale_pool_variable": "custom_pool"})
    payload = run_payload()
    payload["data"]["attributes"]["variables"][0]["key"] = "custom_pool"
    upstream.return_value = response({"data": {"id": "run-owned"}}, 201)
    assert client.post(PREFIX + "runs", headers=HEADERS, json=payload).status_code == 201


@pytest.mark.parametrize("change", ["id", "key", "category", "hcl", "relationships"])
def test_variable_payload_cannot_retarget_or_change_metadata(client, upstream, change):
    payload = patch_payload()
    if change == "id":
        payload["data"]["id"] = "var-other"
    elif change == "relationships":
        payload["data"]["relationships"] = {"workspace": {"data": {"id": "ws-other"}}}
    else:
        payload["data"]["attributes"][change] = {"key": "secret", "category": "env", "hcl": False}[change]
    assert client.patch(PREFIX + f"workspaces/{WORKSPACE}/vars/var-pool", headers=HEADERS, json=payload).status_code == 403
    upstream.assert_not_called()


def test_empty_pool_is_valid_for_suspend(client, upstream):
    upstream.side_effect = [response({"data": [POOL]}), response({"data": POOL})]
    assert client.patch(PREFIX + f"workspaces/{WORKSPACE}/vars/var-pool", headers=HEADERS, json=patch_payload("[]")).status_code == 200


@pytest.mark.parametrize("body", [{}, {"data": None}, {"data": [{}]}, {"data": [{"attributes": None}]}])
def test_malformed_variable_lookup_cannot_authorize_write(client, upstream, body):
    upstream.return_value = response(body)
    result = client.patch(PREFIX + f"workspaces/{WORKSPACE}/vars/var-pool", headers=HEADERS, json=patch_payload())
    assert result.status_code == 502
    assert upstream.call_count == 1


def test_token_without_workspace_is_denied(client, upstream):
    cluster = db.session.scalar(db.select(MagicCastleORM).where(MagicCastleORM.cluster_token == "cluster-token"))
    cluster.tfcloud_workspace = None
    db.session.commit()
    assert client.get(PREFIX + f"workspaces/{WORKSPACE}", headers=HEADERS).status_code == 403
    upstream.assert_not_called()
