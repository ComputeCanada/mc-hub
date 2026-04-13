import re

import requests
from flask import request, Response

from ..database import db
from ..models.magic_castle.magic_castle import MagicCastleORM
from ..services.terraform_cloud_api import get_terraform_cloud
from ..exceptions.invalid_usage_exception import InvalidUsageException, UnauthenticatedException

BEARER_RE = re.compile(r"^Bearer\s+(.+)$", re.IGNORECASE)
WORKSPACE_PATH_RE = re.compile(r"^workspaces/([^/]+)")


def tfcloud_proxy(path):
    # Extract Bearer token
    auth_header = request.headers.get("Authorization", "")
    match = BEARER_RE.match(auth_header)
    if not match:
        raise UnauthenticatedException()
    cluster_token = match.group(1)

    # Look up cluster by token
    cluster_orm = db.session.execute(
        db.select(MagicCastleORM).filter_by(cluster_token=cluster_token)
    ).scalar_one_or_none()
    if cluster_orm is None:
        raise UnauthenticatedException()

    # Scope enforcement: workspace paths must match the cluster's workspace
    workspace_match = WORKSPACE_PATH_RE.match(path)
    if workspace_match and workspace_match.group(1) != cluster_orm.tfcloud_workspace:
        raise InvalidUsageException("Access to this workspace is not allowed", status_code=403)

    # Scope enforcement: run creation must target the cluster's workspace
    if path == "runs" and request.method == "POST":
        body = request.get_json(silent=True) or {}
        run_workspace = (
            body.get("data", {})
            .get("relationships", {})
            .get("workspace", {})
            .get("data", {})
            .get("id")
        )
        if run_workspace and run_workspace != cluster_orm.tfcloud_workspace:
            raise InvalidUsageException("Access to this workspace is not allowed", status_code=403)

    # Forward to TF Cloud
    tf = get_terraform_cloud()
    url = f"{tf.BASE_URL}/{path}"
    resp = requests.request(
        method=request.method,
        url=url,
        headers={
            **tf.headers,
            "Content-Type": request.content_type or "application/vnd.api+json",
            "Accept": request.headers.get("Accept", "application/vnd.api+json"),
        },
        data=request.get_data(),
        params=request.args,
        timeout=30,
    )

    return Response(
        resp.content,
        status=resp.status_code,
        content_type=resp.headers.get("Content-Type"),
    )
