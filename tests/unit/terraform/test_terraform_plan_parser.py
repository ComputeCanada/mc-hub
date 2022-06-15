import pytest

import tests
import json

from mchub.models.terraform.terraform_plan_parser import TerraformPlanParser

from ...test_helpers import *  # noqa
from ...mocks.configuration.config_mock import config_auth_none_mock  # noqa;
from ...data import PROGRESS_DATA


def load_plan(hostname):
    state_file_path = path.join(
        path.dirname(tests.__file__),
        "data",
        "mock-clusters",
        hostname,
        f"terraform_plan.json",
    )
    with open(state_file_path, "r") as terraform_state_file:
        return json.load(terraform_state_file)


def read_terraform_apply_log(hostname):
    terraform_apply_output_path = path.join(
        path.dirname(tests.__file__),
        "data",
        "mock-clusters",
        hostname,
        f"terraform_apply.log",
    )
    with open(terraform_apply_output_path, "r") as terraform_apply_output_file:
        return terraform_apply_output_file.read()


@pytest.fixture
def missing_floating_ips_initial_plan():
    return load_plan("missingfloatingips.c3.ca")


def test_get_resources_changes():
    plan = {
        "format_version": "0.2",
        "terraform_version": "1.0.7",
        "planned_values": {"root_module": {"child_modules": []}},
        "resource_changes": [
            {
                "address": "module.openstack.module.cluster_config.null_resource.deploy_hieradata[0]",
                "module_address": "module.openstack.module.cluster_config",
                "type": "null_resource",
                "name": "deploy_hieradata",
                "change": {
                    "actions": ["create"],
                    "before": None,
                    "after": {},
                    "after_unknown": {"id": True, "triggers": True},
                    "before_sensitive": False,
                    "after_sensitive": {"triggers": {}},
                },
            },
        ],
        "prior_state": {},
        "configuration": {},
    }
    result = [
        {
            "address": "module.openstack.module.cluster_config.null_resource.deploy_hieradata[0]",
            "type": "null_resource",
            "change": {"actions": ["create"]},
        }
    ]
    assert TerraformPlanParser.get_resources_changes(plan) == result


def test_get_done_changes(missing_floating_ips_initial_plan):
    progress = TerraformPlanParser.get_done_changes(
        missing_floating_ips_initial_plan,
        read_terraform_apply_log("missingfloatingips.c3.ca"),
    )
    assert progress == PROGRESS_DATA["progress"]
