from copy import deepcopy

import pytest

from ...data import VALID_CLUSTER_CONFIGURATION
from ...mocks.configuration.config_mock import config_auth_none_mock as config_mock  # noqa: F401
from ...test_helpers import (  # noqa: F401
    app,
    generate_test_clusters,
    mock_clusters_path,
    mock_github_storage_api,
    mock_terraform_cloud_api,
)


@pytest.mark.parametrize("zone", ["ca-central-1b", None, ""])
def test_aws_zone_is_committed_on_creation_and_rebuild(app, mocker, zone):
    from mchub.database import db
    from mchub.models.cloud.project import Project, Provider
    from mchub.models.magic_castle.magic_castle import MagicCastle, MagicCastleORM
    from mchub.services.github_api import get_github_storage

    project = db.session.get(Project, VALID_CLUSTER_CONFIGURATION["cloud"]["id"])
    project.provider = Provider.AWS
    project.env = {"AWS_DEFAULT_REGION": "ca-central-1"}
    write = mocker.spy(get_github_storage(), "write")
    cluster = MagicCastle()
    cluster.plan_creation({**deepcopy(VALID_CLUSTER_CONFIGURATION), "availability_zone": "ca-central-1a"})
    assert write.call_args.args[0]["availability_zone"] == "ca-central-1a"

    write.reset_mock()
    cluster.plan_modification({**cluster.state, "availability_zone": zone})
    hostname = cluster.hostname
    db.session.remove()
    cluster = MagicCastle(db.session.scalar(db.select(MagicCastleORM).filter_by(hostname=hostname)))
    cluster.plan_rebuild()

    write.assert_called_once()
    variables, committed_hostname = write.call_args.args
    assert committed_hostname == hostname
    assert variables["region"] == "ca-central-1"
    if zone:
        assert variables["availability_zone"] == zone
    else:
        assert "availability_zone" not in variables
