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


@pytest.mark.parametrize("subnet", ["subnet-selected", None])
def test_project_subnet_is_committed_on_creation_modification_and_rebuild(app, mocker, subnet):
    from mchub.database import db
    from mchub.models.cloud.project import Project
    from mchub.models.magic_castle.magic_castle import MagicCastle
    from mchub.services.github_api import get_github_storage

    project = db.session.get(Project, VALID_CLUSTER_CONFIGURATION["cloud"]["id"])
    if subnet:
        project.env = {**project.env, "OS_SUBNET_ID": subnet}
    write = mocker.spy(get_github_storage(), "write")
    cluster = MagicCastle()
    cluster.plan_creation(deepcopy(VALID_CLUSTER_CONFIGURATION))
    updated = {**cluster.state, "nb_users": 42}
    cluster.orm.undeployed = False
    cluster.plan_modification(updated)
    cluster.orm.undeployed = True
    cluster.plan_rebuild()
    assert write.call_count == 3
    for call in write.call_args_list:
        variables = call.args[0]
        if subnet:
            assert variables["subnet_id"] == subnet
        else:
            assert "subnet_id" not in variables
