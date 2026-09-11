"""Workspace-scoped Terraform API access for slurm-autoscale-tfe."""
import json
import re

import requests
from flask import request, Response

from .api_view import handle_exceptions
from ..configuration import get_config
from ..database import db
from ..models.magic_castle.magic_castle import MagicCastleORM
from ..services.terraform_cloud_api import get_terraform_cloud
from ..exceptions.invalid_usage_exception import InvalidUsageException

BEARER_RE = re.compile(r"^Bearer\s+(.+)$", re.IGNORECASE)
WORKSPACE_ROUTE = re.compile(r"workspaces/(ws-[A-Za-z0-9]+)(?:/(vars|resources)(?:/(var-[A-Za-z0-9]+))?)?")
RUN_ROUTE = re.compile(r"runs/(run-[A-Za-z0-9]+)")
JSON_API = "application/vnd.api+json"


def deny():
    raise InvalidUsageException("This Terraform operation is not allowed for this cluster.", status_code=403)


def exact_keys(value, keys):
    if not isinstance(value, dict) or set(value) != set(keys):
        deny()
    return value


def pool_value(value):
    # JSON arrays are also valid HCL; arbitrary HCL expressions are not needed.
    try:
        hosts = json.loads(value) if isinstance(value, str) else None
    except ValueError:
        deny()
    if not isinstance(hosts, list) or any(not isinstance(host, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+", host) for host in hosts):
        deny()


def upstream(tf, method, path, **kwargs):
    try:
        response = requests.request(
            method=method,
            url=f"{tf.BASE_URL}/{path}",
            headers={**tf.headers, "Content-Type": JSON_API, "Accept": JSON_API},
            timeout=30,
            allow_redirects=False,
            **kwargs,
        )
    except requests.RequestException:
        raise InvalidUsageException("Terraform Cloud request failed.", status_code=502)
    # Never follow redirects with the operator credential or return unchecked bodies.
    if not 200 <= response.status_code < 300:
        status = response.status_code if 400 <= response.status_code < 500 else 502
        raise InvalidUsageException("Terraform Cloud could not complete this operation.", status_code=status)
    return response


def document(response):
    try:
        body = response.json()
        if not isinstance(body, dict):
            raise ValueError
        return body
    except ValueError:
        raise InvalidUsageException("Invalid Terraform Cloud response.", status_code=502)


def pool_variables(tf, workspace, pool_name):
    # Scan pages using our own fixed route, never an upstream-supplied URL.
    page = 1
    result = []
    while True:
        body = document(upstream(tf, "GET", f"workspaces/{workspace}/vars",
                                 params={"page[number]": page, "page[size]": 100}))
        variables = body.get("data")
        if not isinstance(variables, list) or any(not isinstance(v, dict) for v in variables):
            raise InvalidUsageException("Invalid Terraform Cloud variables response.", status_code=502)
        for variable in variables:
            attrs = variable.get("attributes")
            if not isinstance(attrs, dict):
                raise InvalidUsageException("Invalid Terraform Cloud variables response.", status_code=502)
            if attrs.get("key") == pool_name and attrs.get("category") == "terraform":
                result.append(variable)
        links = body.get("links") or {}
        if not isinstance(links, dict):
            raise InvalidUsageException("Invalid Terraform Cloud variables response.", status_code=502)
        if not links.get("next"):
            return result
        page += 1


@handle_exceptions
def tfcloud_proxy(path):
    match = BEARER_RE.fullmatch(request.headers.get("Authorization", ""))
    if not match:
        raise InvalidUsageException("Invalid or missing cluster token.", status_code=401)
    cluster = db.session.execute(
        db.select(MagicCastleORM).filter_by(cluster_token=match.group(1))
    ).scalar_one_or_none()
    if cluster is None:
        raise InvalidUsageException("Invalid or missing cluster token.", status_code=401)
    workspace = cluster.tfcloud_workspace
    if not workspace:
        deny()

    workspace_route = WORKSPACE_ROUTE.fullmatch(path)
    run_route = RUN_ROUTE.fullmatch(path)
    method = request.method
    if workspace_route:
        workspace_id, resource, variable_id = workspace_route.groups()
        if workspace_id != workspace:
            deny()
        if not ((method == "GET" and variable_id is None)
                or (method == "PATCH" and resource == "vars" and variable_id is not None)):
            deny()
    elif not ((method == "POST" and path == "runs") or (method == "GET" and run_route)):
        deny()

    # Only resource pagination is used by the client; reject include, filters, etc.
    params = {}
    for key, values in request.args.lists():
        if not (method == "GET" and workspace_route and workspace_route.group(2) == "resources"
                and key in {"page[number]", "page[size]"} and len(values) == 1
                and re.fullmatch(r"[1-9][0-9]{0,5}", values[0])):
            deny()
        params[key] = values[0]
    if method == "GET" and request.get_data():
        deny()

    pool_name = get_config().get("tfcloud_autoscale_pool_variable", "pool")
    payload = None
    if method == "PATCH":
        body = exact_keys(request.get_json(silent=True), {"data"})
        data = exact_keys(body["data"], {"type", "id", "attributes"})
        attrs = exact_keys(data["attributes"], {"value", "hcl", "category"})
        if data["type"] != "vars" or data["id"] != variable_id or attrs["hcl"] is not True or attrs["category"] != "terraform":
            deny()
        pool_value(attrs["value"])
        payload = body
    elif method == "POST":
        body = exact_keys(request.get_json(silent=True), {"data"})
        data = exact_keys(body["data"], {"type", "attributes", "relationships"})
        relationships = exact_keys(data["relationships"], {"workspace"})
        reference = exact_keys(exact_keys(relationships["workspace"], {"data"})["data"], {"type", "id"})
        if data["type"] != "runs" or reference != {"type": "workspaces", "id": workspace}:
            deny()
        attrs = exact_keys(data["attributes"], {"message", "target-addrs", "auto-apply", "variables"})
        if not isinstance(attrs["message"], str) or attrs["auto-apply"] is not True:
            deny()
        if not isinstance(attrs["target-addrs"], list) or any(not isinstance(target, str) for target in attrs["target-addrs"]):
            deny()
        variables = attrs["variables"]
        if not isinstance(variables, list) or len(variables) != 1:
            deny()
        variable = exact_keys(variables[0], {"key", "value"})
        if variable["key"] != pool_name:
            deny()
        pool_value(variable["value"])
        payload = body

    tf = get_terraform_cloud()
    if workspace_route and workspace_route.group(2) == "vars":
        variables = pool_variables(tf, workspace, pool_name)
        if method == "GET":
            return {"data": variables, "links": {"next": None}}
        if not any(v.get("id") == variable_id for v in variables):
            deny()

    kwargs = {"params": params} if method == "GET" else {"json": payload}
    response = upstream(tf, method, path, **kwargs)
    if run_route:
        body = document(response)
        try:
            run_workspace = body["data"]["relationships"]["workspace"]["data"]["id"]
        except (KeyError, TypeError):
            deny()
        if run_workspace != workspace:
            deny()
        # Ownership is checked on the same response returned to the caller.
    return Response(response.content, status=response.status_code, content_type=JSON_API)
