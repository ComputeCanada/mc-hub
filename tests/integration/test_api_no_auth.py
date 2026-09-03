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
        assert result == CLUSTERS[cluster_name]


# GET /api/magic-castles/<hostname>
@freeze_time("2022-01-01")
@pytest.mark.usefixtures("mock_status_logic")
def test_get_state_existing(client):
    res = client.get(f"/api/magic-castles/{EXISTING_HOSTNAME}")
    state = res.get_json()
    assert state == EXISTING_CLUSTER_STATE
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
    background_task.assert_called_once()


def test_delete_marks_cluster_busy_before_starting_worker(client, mocker):
    from mchub.database import db
    from mchub.models.magic_castle.cluster_status_code import ClusterStatusCode
    from mchub.models.magic_castle.magic_castle import MagicCastleORM
    from mchub.resources.magic_castle_api import MagicCastleAPI

    background_task = mocker.patch.object(MagicCastleAPI, "_run_in_background")

    res = client.delete(f"/api/magic-castles/{EXISTING_HOSTNAME}")

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
