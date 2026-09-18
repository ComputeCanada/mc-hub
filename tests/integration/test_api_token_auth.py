import pytest

from mchub.configuration import get_config
from mchub.database import db
from mchub.models.auth_type import AuthType
from mchub.models.magic_castle.cluster_status_code import ClusterStatusCode
from mchub.models.magic_castle.magic_castle import MagicCastleORM
from mchub.resources.magic_castle_api import MagicCastleAPI

from ..data import EXISTING_HOSTNAME, NON_EXISTING_HOSTNAME
from ..mocks.configuration.config_mock import config_auth_saml_mock as config_mock
from ..test_helpers import app, client, generate_test_clusters, mock_clusters_path


@pytest.fixture
def token_headers(config_mock, mocker):
    config = get_config()
    mocker.patch.dict(config, {"auth_type": [AuthType.TOKEN]})
    return {"Authorization": f"token {config['token']}"}


def test_token_can_teardown_cluster(client, token_headers, mocker):
    background_task = mocker.patch.object(MagicCastleAPI, "_run_in_background")

    response = client.post(
        f"/api/magic-castles/{EXISTING_HOSTNAME}/teardown", headers=token_headers
    )

    assert response.status_code == 202
    orm = db.session.scalar(
        db.select(MagicCastleORM).filter_by(hostname=EXISTING_HOSTNAME)
    )
    assert orm.status == ClusterStatusCode.BACKGROUND_TASK_RUNNING
    background_task.assert_called_once()
    assert background_task.call_args.kwargs == {"hostname": EXISTING_HOSTNAME}


@pytest.mark.parametrize("headers", [{}, {"Authorization": "token invalid"}])
def test_teardown_requires_valid_token(client, token_headers, mocker, headers):
    background_task = mocker.patch.object(MagicCastleAPI, "_run_in_background")

    response = client.post(
        f"/api/magic-castles/{EXISTING_HOSTNAME}/teardown", headers=headers
    )

    assert response.status_code == 400
    assert response.get_json() == {"message": "You need to be authenticated."}
    background_task.assert_not_called()


def test_token_teardown_unknown_cluster(client, token_headers, mocker):
    background_task = mocker.patch.object(MagicCastleAPI, "_run_in_background")

    response = client.post(
        f"/api/magic-castles/{NON_EXISTING_HOSTNAME}/teardown", headers=token_headers
    )

    assert response.get_json() == {"message": "This cluster does not exist."}
    assert response.status_code == 400
    background_task.assert_not_called()
