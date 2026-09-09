from ..test_helpers import (
    client,
    app,
    generate_test_clusters,
    mock_clusters_path,
    mock_terraform_cloud_api,
    mock_status_logic,
)
from ..mocks.configuration.config_mock import (
    config_auth_none_mock as config_mock,
)  # noqa;
from subprocess import getoutput
from getpass import getuser

from freezegun import freeze_time

from ..data import (
    NON_EXISTING_CLUSTER_CONFIGURATION,
    EXISTING_CLUSTER_CONFIGURATION,
    EXISTING_HOSTNAME,
    NON_EXISTING_HOSTNAME,
    EXISTING_CLUSTER_STATE,
    CLUSTERS,
    PROGRESS_DATA,
    DEFAULT_TEMPLATE,
)


# GET /api/users/me
def test_get_current_user(client):
    res = client.get(f"/api/users/me")
    assert res.get_json() == {
        "username": getuser(),
        "public_keys": getoutput("ssh-add -L").split("\n"),
        "usertype": "local",
    }


def test_get_current_user(client):
    res = client.get(f"/api/template/default")
    assert res.get_json() == DEFAULT_TEMPLATE


import pytest


# GET /api/magic_castle
@freeze_time("2022-01-01")
@pytest.mark.usefixtures("mock_status_logic")
def test_get_all_magic_castle_names(client):
    res = client.get(f"/api/magic-castles")
    assert res.status_code == 200
    for result in res.get_json():
        cluster_name = result["hostname"]
        assert result == {**CLUSTERS[cluster_name], "undeployed": False}


# GET /api/magic-castles/<hostname>
@freeze_time("2022-01-01")
@pytest.mark.usefixtures("mock_status_logic")
def test_get_state_existing(client):
    res = client.get(f"/api/magic-castles/{EXISTING_HOSTNAME}")
    state = res.get_json()
    assert state == {**EXISTING_CLUSTER_STATE, "undeployed": False}
    assert res.status_code == 200


def test_get_state_non_existing(client):
    res = client.get(f"/api/magic-castles/{NON_EXISTING_HOSTNAME}")
    assert res.get_json() == {"message": "This cluster does not exist."}
    assert res.status_code != 200


def test_apply_rejects_cluster_while_plan_is_running(client, mocker):
    from mchub.database import db
    from mchub.models.magic_castle.cluster_status_code import ClusterStatusCode
    from mchub.models.magic_castle.magic_castle import MagicCastleORM
    from mchub.resources.magic_castle_api import MagicCastleAPI

    orm = db.session.scalar(
        db.select(MagicCastleORM).filter_by(hostname=EXISTING_HOSTNAME)
    )
    orm.status = ClusterStatusCode.PLAN_RUNNING
    db.session.commit()
    background_task = mocker.patch.object(MagicCastleAPI, "_run_in_background")

    res = client.post(f"/api/magic-castles/{EXISTING_HOSTNAME}/apply")

    assert res.status_code == 400
    assert res.get_json() == {"message": "This cluster is busy."}
    background_task.assert_not_called()


def test_apply_rejects_missing_plan_before_starting_worker(client, mocker):
    from mchub.database import db
    from mchub.models.magic_castle.cluster_status_code import ClusterStatusCode
    from mchub.models.magic_castle.magic_castle import MagicCastleORM
    from mchub.resources.magic_castle_api import MagicCastleAPI

    orm = db.session.scalar(
        db.select(MagicCastleORM).filter_by(hostname=EXISTING_HOSTNAME)
    )
    orm.status = ClusterStatusCode.CREATED
    orm.tfcloud_run.plan = None
    db.session.commit()
    background_task = mocker.patch.object(MagicCastleAPI, "_run_in_background")

    res = client.post(f"/api/magic-castles/{EXISTING_HOSTNAME}/apply")

    assert res.status_code == 400
    assert res.get_json() == {
        "message": "The terraform plan for this cluster does not exist."
    }
    background_task.assert_not_called()


def test_apply_rejects_stale_plan_after_plan_error(client, mocker):
    from mchub.database import db
    from mchub.models.magic_castle.cluster_status_code import ClusterStatusCode
    from mchub.models.magic_castle.magic_castle import MagicCastleORM
    from mchub.resources.magic_castle_api import MagicCastleAPI

    orm = db.session.scalar(
        db.select(MagicCastleORM).filter_by(hostname=EXISTING_HOSTNAME)
    )
    orm.status = ClusterStatusCode.PLAN_ERROR
    orm.tfcloud_run.run_id = "STALE_RUN"
    orm.tfcloud_run.plan = {"STALE": "PLAN"}
    db.session.commit()
    background_task = mocker.patch.object(MagicCastleAPI, "_run_in_background")

    res = client.post(f"/api/magic-castles/{EXISTING_HOSTNAME}/apply")

    assert res.status_code == 400
    assert res.get_json() == {
        "message": "The terraform plan for this cluster is not ready to apply."
    }
    background_task.assert_not_called()


def test_apply_starts_worker_when_plan_is_ready(client, mocker):
    from mchub.database import db
    from mchub.models.magic_castle.cluster_status_code import ClusterStatusCode
    from mchub.models.magic_castle.magic_castle import MagicCastleORM
    from mchub.resources.magic_castle_api import MagicCastleAPI

    orm = db.session.scalar(
        db.select(MagicCastleORM).filter_by(hostname=EXISTING_HOSTNAME)
    )
    orm.status = ClusterStatusCode.CREATED
    orm.tfcloud_run.run_id = "READY_RUN"
    orm.tfcloud_run.plan = {"READY": "PLAN"}
    db.session.commit()
    background_task = mocker.patch.object(MagicCastleAPI, "_run_in_background")

    res = client.post(f"/api/magic-castles/{EXISTING_HOSTNAME}/apply")

    assert res.status_code == 202
    orm = db.session.scalar(
        db.select(MagicCastleORM).filter_by(hostname=EXISTING_HOSTNAME)
    )
    assert orm.status == ClusterStatusCode.BACKGROUND_TASK_RUNNING
    background_task.assert_called_once()


def test_apply_claim_prevents_second_worker(client, mocker):
    from mchub.database import db
    from mchub.models.magic_castle.cluster_status_code import ClusterStatusCode
    from mchub.models.magic_castle.magic_castle import MagicCastleORM
    from mchub.resources.magic_castle_api import MagicCastleAPI

    orm = db.session.scalar(
        db.select(MagicCastleORM).filter_by(hostname=EXISTING_HOSTNAME)
    )
    orm.status = ClusterStatusCode.CREATED
    orm.tfcloud_run.run_id = "READY_RUN"
    orm.tfcloud_run.plan = {"READY": "PLAN"}
    db.session.commit()
    background_task = mocker.patch.object(MagicCastleAPI, "_run_in_background")

    first = client.post(f"/api/magic-castles/{EXISTING_HOSTNAME}/apply")
    second = client.post(f"/api/magic-castles/{EXISTING_HOSTNAME}/apply")

    assert first.status_code == 202
    assert second.status_code == 400
    assert second.get_json() == {"message": "This cluster is busy."}
    background_task.assert_called_once()


def test_teardown_marks_cluster_busy_before_starting_worker(client, mocker):
    from mchub.database import db
    from mchub.models.magic_castle.cluster_status_code import ClusterStatusCode
    from mchub.models.magic_castle.magic_castle import MagicCastleORM
    from mchub.resources.magic_castle_api import MagicCastleAPI

    background_task = mocker.patch.object(MagicCastleAPI, "_run_in_background")

    res = client.post(f"/api/magic-castles/{EXISTING_HOSTNAME}/teardown")

    assert res.status_code == 202
    orm = db.session.scalar(
        db.select(MagicCastleORM).filter_by(hostname=EXISTING_HOSTNAME)
    )
    assert orm.status == ClusterStatusCode.BACKGROUND_TASK_RUNNING
    background_task.assert_called_once()


# TODO: Fix this?
# GET /api/magic-castles/<hostname>/status
# def test_get_status(mocker, client):
#     res = client.get(f"/api/magic-castles/missingfloatingips.mc.ca/status")
#     assert res.get_json() == PROGRESS_DATA


@pytest.mark.usefixtures("mock_status_logic")
def test_get_status_code(client):
    from mchub.models.magic_castle.cluster_status_code import ClusterStatusCode
    from mchub.models.magic_castle.magic_castle import MagicCastleORM
    from mchub.database import db

    res = client.get(f"/api/magic-castles/{NON_EXISTING_HOSTNAME}/status")
    assert res.get_json()["status"] == "not_found"

    orm = db.session.scalar(
        db.select(MagicCastleORM).filter_by(hostname=EXISTING_HOSTNAME)
    )
    orm.status = ClusterStatusCode.BUILD_RUNNING
    db.session.commit()
    res = client.get(f"/api/magic-castles/{EXISTING_HOSTNAME}/status")
    assert res.get_json()["status"] == "build_running"

    orm = db.session.scalar(
        db.select(MagicCastleORM).filter_by(hostname=EXISTING_HOSTNAME)
    )
    orm.status = ClusterStatusCode.PROVISIONING_SUCCESS
    db.session.commit()
    res = client.get(f"/api/magic-castles/{EXISTING_HOSTNAME}/status")
    assert res.get_json()["status"] == "provisioning_success"

    orm = db.session.scalar(
        db.select(MagicCastleORM).filter_by(hostname=EXISTING_HOSTNAME)
    )
    orm.status = ClusterStatusCode.BUILD_ERROR
    db.session.commit()
    res = client.get(f"/api/magic-castles/{EXISTING_HOSTNAME}/status")
    assert res.get_json()["status"] == "build_error"

    orm = db.session.scalar(
        db.select(MagicCastleORM).filter_by(hostname=EXISTING_HOSTNAME)
    )
    orm.status = ClusterStatusCode.DESTROY_RUNNING
    db.session.commit()
    res = client.get(f"/api/magic-castles/{EXISTING_HOSTNAME}/status")
    assert res.get_json()["status"] == "destroy_running"

    orm = db.session.scalar(
        db.select(MagicCastleORM).filter_by(hostname=EXISTING_HOSTNAME)
    )
    orm.status = ClusterStatusCode.DESTROY_ERROR
    db.session.commit()
    res = client.get(f"/api/magic-castles/{EXISTING_HOSTNAME}/status")
    assert res.get_json()["status"] == "destroy_error"


# TODO: is_busy is not present with tf_cloud
# # DELETE /api/magic-castles/<hostname>
# def test_delete_invalid_status(client):
#     from mchub.models.magic_castle.cluster_status_code import ClusterStatusCode
#     from mchub.models.magic_castle.magic_castle import MagicCastleORM
#     from mchub.database import db
#
#     res = client.delete(f"/api/magic-castles/{NON_EXISTING_HOSTNAME}")
#     assert res.get_json() == {"message": "This cluster does not exist."}
#     assert res.status_code != 200
#
#     orm = db.session.scalar(
#         db.select(MagicCastleORM).filter_by(hostname=EXISTING_HOSTNAME)
#     )
#     orm.status = ClusterStatusCode.DESTROY_RUNNING
#     db.session.commit()
#     res = client.delete(f"/api/magic-castles/{EXISTING_HOSTNAME}")
#     assert res.get_json() == {"message": "This cluster is busy."}
#     assert res.status_code != 200
#
#     orm = db.session.scalar(
#         db.select(MagicCastleORM).filter_by(hostname=EXISTING_HOSTNAME)
#     )
#     orm.status = ClusterStatusCode.BUILD_RUNNING
#     db.session.commit()
#     res = client.delete(f"/api/magic-castles/{EXISTING_HOSTNAME}")
#     assert res.get_json() == {"message": "This cluster is busy."}
#     assert res.status_code != 200


# PUT /api/magic-castles/<hostname>
def test_modify_invalid_status(client):
    from mchub.models.magic_castle.cluster_status_code import ClusterStatusCode
    from mchub.models.magic_castle.magic_castle import MagicCastleORM
    from mchub.database import db

    res = client.put(
        f"/api/magic-castles/{NON_EXISTING_HOSTNAME}",
        json=NON_EXISTING_CLUSTER_CONFIGURATION,
    )
    assert res.get_json() == {"message": "This cluster does not exist."}
    assert res.status_code != 200

    # orm = db.session.scalar(
    #     db.select(MagicCastleORM).filter_by(hostname=EXISTING_HOSTNAME)
    # )
    # orm.status = ClusterStatusCode.BUILD_RUNNING
    # db.session.commit()
    # res = client.put(
    #     f"/api/magic-castles/{EXISTING_HOSTNAME}",
    #     json=EXISTING_CLUSTER_CONFIGURATION,
    # )
    # assert res.get_json() == {"message": "This cluster is busy."}
    # assert res.status_code != 200

    # orm = db.session.scalar(
    #     db.select(MagicCastleORM).filter_by(hostname=EXISTING_HOSTNAME)
    # )
    # orm.status = ClusterStatusCode.DESTROY_RUNNING
    # db.session.commit()
    # res = client.put(
    #     f"/api/magic-castles/{EXISTING_HOSTNAME}",
    #     json=EXISTING_CLUSTER_CONFIGURATION,
    # )
    # assert res.get_json() == {"message": "This cluster is busy."}
    # assert res.status_code != 200


def test_delete_requires_verified_empty_workspace_and_restores_status_on_rejection(client, mocker):
    mocker.patch("mchub.models.magic_castle.magic_castle.get_github_storage")
    from mchub.database import db
    from mchub.models.magic_castle.magic_castle import MagicCastleORM
    from mchub.services.terraform_cloud_api import get_terraform_cloud
    from mchub.exceptions.invalid_usage_exception import InvalidUsageException

    orm = db.session.scalar(db.select(MagicCastleORM).filter_by(hostname=EXISTING_HOSTNAME))
    previous_status = orm.status
    orm.tfcloud_workspace = "ws-retained"
    db.session.commit()
    tf = get_terraform_cloud()
    mocker.patch.object(tf, "lock_workspace", create=True)
    mocker.patch.object(tf, "unlock_workspace", create=True)
    verify = mocker.patch.object(tf, "verify_workspace_empty", create=True, side_effect=InvalidUsageException("resources remain"))
    response = client.delete(f"/api/magic-castles/{EXISTING_HOSTNAME}")
    assert response.status_code == 400
    assert orm.status == previous_status
    verify.side_effect = None
    response = client.delete(f"/api/magic-castles/{EXISTING_HOSTNAME}")
    assert response.status_code == 204
    assert db.session.scalar(db.select(MagicCastleORM).filter_by(hostname=EXISTING_HOSTNAME)) is None


@pytest.mark.parametrize("discard_fails", [False, True])
def test_declining_teardown_restores_deployment_only_after_discard(client, mocker, discard_fails):
    import json
    from pathlib import Path
    from mchub.database import db
    from mchub.models.magic_castle.magic_castle import MagicCastle, MagicCastleORM
    from mchub.models.magic_castle.cluster_status_code import ClusterStatusCode
    from mchub.models.magic_castle.terraform_cloud_status import TFCloudStatusCode
    from mchub.services.terraform_cloud_api import get_terraform_cloud
    from mchub.exceptions.server_exception import TerraformCloudException

    orm = db.session.scalar(db.select(MagicCastleORM).filter_by(hostname=EXISTING_HOSTNAME))
    cluster = MagicCastle(orm)
    orm.tfcloud_workspace = "existing-workspace"
    cluster.create_plan(run_id="destroy-run")
    assert cluster.tf_state is None
    tf = get_terraform_cloud()
    mocker.patch.object(tf, "get_run_status", return_value=(TFCloudStatusCode.PLANNED, True))
    state_path = Path(__file__).resolve().parents[1] / "data/mock-clusters/valid1.magic-castle.cloud/terraform.tfstate"
    state = json.loads(state_path.read_text())
    mocker.patch.object(tf, "get_tf_state", return_value=state)
    discard = mocker.patch.object(tf, "discard_run", create=True,
        side_effect=TerraformCloudException("discard rejected") if discard_fails else None)

    response = client.post(f"/api/magic-castles/{EXISTING_HOSTNAME}/discard-teardown")

    discard.assert_called_once_with("destroy-run")
    if discard_fails:
        assert response.status_code >= 400
        assert orm.status == ClusterStatusCode.CREATED
        assert cluster.tfcloud_run.run_id == "destroy-run"
        assert cluster.plan is not None
    else:
        assert response.status_code == 204
        assert cluster.status == ClusterStatusCode.PROVISIONING_SUCCESS
        assert cluster.tf_state is not None
        assert cluster.plan is None
        assert cluster.tfcloud_run.run_id is None
        assert not orm.undeployed
        response = client.post(f"/api/magic-castles/{EXISTING_HOSTNAME}/apply")
        assert response.status_code >= 400
        assert cluster.status == ClusterStatusCode.PROVISIONING_SUCCESS


def test_discard_teardown_rejects_a_build_plan(client, mocker):
    from mchub.database import db
    from mchub.models.magic_castle.magic_castle import MagicCastle, MagicCastleORM
    from mchub.services.terraform_cloud_api import get_terraform_cloud
    orm = db.session.scalar(db.select(MagicCastleORM).filter_by(hostname=EXISTING_HOSTNAME))
    cluster = MagicCastle(orm)
    orm.tfcloud_workspace = "existing-workspace"
    cluster.create_plan(run_id="build-run")
    discard = mocker.patch.object(get_terraform_cloud(), "discard_run", create=True)
    response = client.post(f"/api/magic-castles/{EXISTING_HOSTNAME}/discard-teardown")
    assert response.status_code >= 400
    discard.assert_not_called()
    assert cluster.tfcloud_run.run_id == "build-run"
