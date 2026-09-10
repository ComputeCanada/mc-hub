from types import SimpleNamespace
from threading import Barrier

import boto3
import pytest
from botocore.stub import Stubber
from flask import Flask

from mchub.models.cloud.aws_manager import AWSManager, IMAGE_OWNERS, CATALOG_CACHE, CATALOG_CONDITION
from mchub.models.cloud.project import ENV_VALIDATORS, Provider
from mchub.models.terraform.terraform_state import TerraformState
from mchub.exceptions.invalid_usage_exception import InvalidUsageException


STANDARD = "Standard (A, C, D, H, I, M, R, T, Z)"
GPU = "G and VT"
ENV = {"AWS_ACCESS_KEY_ID": "test", "AWS_SECRET_ACCESS_KEY": "secret", "AWS_DEFAULT_REGION": "ca-central-1"}


@pytest.fixture(autouse=True)
def clear_catalog_cache():
    with CATALOG_CONDITION:
        CATALOG_CACHE.clear()
    yield
    with CATALOG_CONDITION:
        CATALOG_CACHE.clear()


@pytest.fixture
def manager(mocker):
    session = boto3.Session(aws_access_key_id="test", aws_secret_access_key="secret", region_name="ca-central-1")
    manager = AWSManager(SimpleNamespace(env=ENV), session=session)
    mocker.patch.object(manager, "read_prices", return_value={})
    manager.prices = {}
    manager.quotas_by_name = {
        f"Running On-Demand {STANDARD} instances": 16,
        f"Running On-Demand {GPU} instances": 8,
        "Storage for General Purpose SSD (gp2) volumes, in TiB": 1,
        "EC2-VPC Elastic IPs": 5,
    }
    manager.types = [
        {"name": "m6i.large", "vcpus": 2, "ram": 8192, "quota_pool": STANDARD},
        {"name": "m6i.xlarge", "vcpus": 4, "ram": 16384, "quota_pool": STANDARD},
        {"name": "m6i.2xlarge", "vcpus": 8, "ram": 32768, "quota_pool": STANDARD},
        {"name": "g5.xlarge", "vcpus": 4, "ram": 16384, "quota_pool": GPU},
    ]
    manager.offered_in_all_zones = {t["name"] for t in manager.types}
    manager.all_types = {t["name"]: {"VCpuInfo": {"DefaultVCpus": t["vcpus"]}} for t in manager.types}
    manager.images = [{"ImageId": "ami-test", "Name": "AlmaLinux OS 9"}]
    manager.availability_zones = ["ca-central-1a", "ca-central-1b"]
    manager.inventory = {"instances": [], "volumes": [], "addresses": [], "reservations": []}
    return manager


def definition(count=1, type="m6i.large", tags=None):
    return {"image": "ami-test", "instances": {"node": {"type": type, "count": count, "tags": tags or ["node"]}}, "volumes": {}}


def test_fixed_storage_and_ip_rules(manager):
    demand, issues = manager.demand(definition(3, tags=["proxy", "login", "dtn"]))
    assert not issues
    assert demand == {STANDARD: 6, "gp2": 60, "eips": 3}
    assert manager.demand(definition(tags=["public"]))[0]["eips"] == 0


def test_all_quota_blockers_returned(manager):
    result = manager.evaluate(definition(60, tags=["proxy"]))
    assert result["status"] == "blocked"
    assert {i["resource"] for i in result["issues"]} == {STANDARD, "gp2", "eips"}


def test_independent_compute_pools(manager):
    manager.inventory["instances"] = [{"InstanceId": "i-other", "InstanceType": "m6i.2xlarge", "State": {"Name": "running"}}] * 2
    assert manager.evaluate(definition(type="g5.xlarge"))["status"] == "ready"
    assert manager.evaluate(definition())["status"] == "blocked"


def test_choices_account_for_other_groups_and_count(manager):
    payload = definition(4)
    payload["instances"]["mgmt"] = {"type": "m6i.xlarge", "count": 1, "tags": ["mgmt"]}
    assert manager.choices(payload)["node"] == ["m6i.large"]
    payload["instances"]["node"]["count"] = 2
    assert manager.choices(payload)["node"] == ["m6i.large", "m6i.xlarge", "g5.xlarge"]


def test_invalid_selected_type_can_be_replaced(manager):
    payload = definition(type="invalid")
    assert manager.evaluate(payload)["status"] == "blocked"
    assert "m6i.large" in manager.choices(payload)["node"]


def test_edit_credit_requires_live_counted_resource(manager):
    manager.resource_ids = {"instances": ["i-running", "i-stopped", "i-gone"], "volumes": ["vol-own"], "addresses": ["eipalloc-own"]}
    manager.inventory["instances"] = [
        {"InstanceId": id, "InstanceType": "m6i.xlarge", "State": {"Name": state}}
        for id, state in [("i-running", "running"), ("i-stopped", "stopped"), ("i-other", "running")]
    ]
    manager.inventory["volumes"] = [
        {"VolumeId": "vol-own", "VolumeType": "gp2", "Size": 20, "State": "in-use"},
        {"VolumeId": "vol-unattached", "VolumeType": "gp2", "Size": 100, "State": "available"},
    ]
    manager.inventory["addresses"] = [{"AllocationId": "eipalloc-own"}, {"AllocationId": "eipalloc-other"}]
    assert manager.budget == {STANDARD: 12, GPU: 8, "gp2": 924, "eips": 4}


def test_capacity_reservations_not_double_counted_or_credited(manager):
    manager.resource_ids = {"instances": ["i-own"]}
    manager.inventory["reservations"] = [{"CapacityReservationId": "cr-1", "InstanceType": "m6i.xlarge", "TotalInstanceCount": 3, "State": "active"}]
    manager.inventory["instances"] = [{"InstanceId": "i-own", "InstanceType": "m6i.xlarge", "State": {"Name": "running"}, "CapacityReservationId": "cr-1"}]
    assert manager.budget[STANDARD] == 4


@pytest.mark.parametrize("count", [-1, 1.5, "2", True, None])
def test_reject_invalid_counts(manager, count):
    assert manager.evaluate(definition(count))["status"] == "blocked"


def test_unmatched_volume_tags_and_unapproved_images(manager):
    payload = definition()
    payload.update(image="ami-untrusted", volumes={"nfs": {"home": {"size": 100}}})
    assert {i["code"] for i in manager.evaluate(payload)["issues"]} == {"image", "volumes"}


def test_missing_quota_is_an_error_not_zero(manager):
    del manager.quotas_by_name["EC2-VPC Elastic IPs"]
    with pytest.raises(InvalidUsageException, match="applied eips quota"):
        manager.evaluate(definition())


def test_enabled_regions_and_pagination(manager):
    with Stubber(manager.ec2) as stub:
        stub.add_response("describe_regions", {"Regions": [{"RegionName": "us-east-1"}, {"RegionName": "ca-central-1"}]}, {})
        assert manager.regions() == ["ca-central-1", "us-east-1"]
        stub.add_response("describe_instance_type_offerings", {"InstanceTypeOfferings": [{"InstanceType": "m6i.large"}], "NextToken": "next"}, {"LocationType": "region"})
        stub.add_response("describe_instance_type_offerings", {"InstanceTypeOfferings": [{"InstanceType": "m6i.xlarge"}]}, {"LocationType": "region", "NextToken": "next"})
        assert len(manager.pages(manager.ec2, "describe_instance_type_offerings", "InstanceTypeOfferings", LocationType="region")) == 2
        stub.assert_no_pending_responses()


def test_provider_errors_are_sanitized(manager):
    with Stubber(manager.ec2) as stub:
        stub.add_client_error("describe_regions", service_error_code="UnauthorizedOperation", service_message="secret details")
        with pytest.raises(InvalidUsageException) as error:
            manager.regions()
        assert error.value.status_code == 503
        assert "UnauthorizedOperation" in str(error.value)
        assert "secret details" not in str(error.value)


def test_project_rejected_before_external_creation(mocker):
    from mchub.resources.project_api import ProjectAPI
    validate = mocker.patch.object(AWSManager, "validate_project", side_effect=InvalidUsageException("Missing permission"))
    tf = mocker.patch("mchub.resources.project_api.get_terraform_cloud")
    with Flask(__name__).test_request_context(json={"provider": "aws", "env": ENV, "name": "aws", "github_template": ""}):
        with pytest.raises(InvalidUsageException, match="Missing permission"):
            ProjectAPI().post(SimpleNamespace(is_admin=True))
    validate.assert_called_once()
    tf.assert_not_called()


def test_environment_requires_one_region():
    from marshmallow import ValidationError
    with pytest.raises(ValidationError):
        ENV_VALIDATORS[Provider.AWS]({"AWS_ACCESS_KEY_ID": "a", "AWS_SECRET_ACCESS_KEY": "b"})
    assert ENV_VALIDATORS[Provider.AWS](ENV)["AWS_DEFAULT_REGION"] == "ca-central-1"


def test_aws_state_identifies_resources_and_deduplicates_disks():
    state = {"resources": [
        {"mode": "managed", "type": "aws_instance", "instances": [{"attributes": {"id": "i-1", "ami": "ami-test", "root_block_device": [{"volume_id": "vol-1"}]}}]},
        {"mode": "managed", "type": "aws_ebs_volume", "instances": [{"attributes": {"id": "vol-1"}}]},
        {"mode": "managed", "type": "aws_eip", "instances": [{"attributes": {"id": "eipalloc-1"}}]},
        {"mode": "data", "type": "aws_instance", "instances": [{"attributes": {"id": "i-external"}}]},
    ]}
    parsed = TerraformState(state, cloud="aws")
    assert parsed.resource_ids == {"instances": ["i-1"], "volumes": ["vol-1"], "addresses": ["eipalloc-1"]}


def test_images_exclude_paid_or_oversized_disks(manager):
    del manager.images
    base = {"Name": "AlmaLinux OS 9.6", "CreationDate": "2026-01-01", "BlockDeviceMappings": [{"DeviceName": "/dev/sda1", "Ebs": {"VolumeSize": 10}}]}
    with Stubber(manager.ec2) as stub:
        stub.add_response("describe_images", {"Images": [
            {**base, "ImageId": "ami-valid"},
            {**base, "ImageId": "ami-paid", "ProductCodes": [{"ProductCodeId": "paid", "ProductCodeType": "marketplace"}]},
            {**base, "ImageId": "ami-large", "BlockDeviceMappings": [{"Ebs": {"VolumeSize": 30}}]},
        ]}, {"Owners": IMAGE_OWNERS, "Filters": [
            {"Name": "name", "Values": ["AlmaLinux OS 9*", "Rocky-9-*", "Rocky-9.*"]},
            {"Name": "state", "Values": ["available"]},
            {"Name": "architecture", "Values": ["x86_64"]},
            {"Name": "virtualization-type", "Values": ["hvm"]},
            {"Name": "root-device-type", "Values": ["ebs"]},
        ]})
        assert [im["ImageId"] for im in manager.images] == ["ami-valid"]


def test_catalog_requires_regional_offering_and_supported_architecture(manager):
    del manager.types
    base = {"InstanceType": "m6i.large", "VCpuInfo": {"DefaultVCpus": 2}, "MemoryInfo": {"SizeInMiB": 8192},
            "ProcessorInfo": {"SupportedArchitectures": ["x86_64"]}, "SupportedUsageClasses": ["on-demand"],
            "SupportedRootDeviceTypes": ["ebs"], "SupportedVirtualizationTypes": ["hvm"]}
    manager.all_types = {
        "m6i.large": base,
        "m6i.xlarge": {**base, "InstanceType": "m6i.xlarge"},
        "m6g.large": {**base, "InstanceType": "m6g.large", "ProcessorInfo": {"SupportedArchitectures": ["arm64"]}},
    }
    with Stubber(manager.ec2) as stub:
        stub.add_response("describe_instance_type_offerings", {"InstanceTypeOfferings": [{"InstanceType": "m6i.large"}, {"InstanceType": "m6g.large"}]}, {"LocationType": "region"})
        assert [t["name"] for t in manager.types] == ["m6i.large"]


def test_image_boot_mode_filters_instance_choices(manager):
    manager.images[0]["BootMode"] = "uefi"
    manager.all_types["m6i.large"]["SupportedBootModes"] = ["uefi"]
    assert manager.choices(definition())["node"] == ["m6i.large"]


def test_unknown_instance_options_cannot_bypass_fixed_contract(manager):
    payload = definition()
    payload["instances"]["node"]["spot"] = True
    assert manager.evaluate(payload)["status"] == "blocked"


def test_validation_reads_every_inventory_source(manager, mocker):
    del manager.inventory
    mocker.patch.object(manager, "regions", return_value=["ca-central-1"])
    def pages(client, operation, key, **kwargs):
        if operation == "describe_capacity_reservations":
            raise InvalidUsageException("UnauthorizedOperation")
        return []
    reads = mocker.patch.object(manager, "pages", side_effect=pages)
    with pytest.raises(InvalidUsageException, match="UnauthorizedOperation"):
        manager.validate_project()
    assert {call.args[1] for call in reads.call_args_list} == {
        "describe_instances", "describe_volumes", "describe_addresses", "describe_capacity_reservations",
    }


def test_zone_discovery_only_returns_available_enabled_regional_zones(manager):
    del manager.availability_zones
    base = {"RegionName": "ca-central-1", "ZoneType": "availability-zone", "State": "available", "OptInStatus": "opt-in-not-required"}
    with Stubber(manager.ec2) as stub:
        stub.add_response("describe_availability_zones", {"AvailabilityZones": [
            {**base, "ZoneName": "ca-central-1b"},
            {**base, "ZoneName": "ca-central-1a"},
            {**base, "ZoneName": "us-east-1a", "RegionName": "us-east-1"},
            {**base, "ZoneName": "ca-central-1c", "State": "unavailable"},
            {**base, "ZoneName": "ca-central-1d", "OptInStatus": "not-opted-in"},
            {**base, "ZoneName": "ca-central-1-local", "ZoneType": "local-zone"},
        ]}, {"Filters": [
            {"Name": "region-name", "Values": ["ca-central-1"]},
            {"Name": "zone-type", "Values": ["availability-zone"]},
            {"Name": "state", "Values": ["available"]},
        ]})
        assert manager.availability_zones == ["ca-central-1a", "ca-central-1b"]


def test_zone_filters_types_and_blocks_unavailable_selection(manager):
    payload = {**definition(type="m6i.xlarge"), "availability_zone": "ca-central-1a"}
    with Stubber(manager.ec2) as stub:
        stub.add_response("describe_instance_type_offerings", {
            "InstanceTypeOfferings": [{"InstanceType": "m6i.large"}], "NextToken": "next",
        }, {"LocationType": "availability-zone", "Filters": [{"Name": "location", "Values": ["ca-central-1a"]}]})
        stub.add_response("describe_instance_type_offerings", {"InstanceTypeOfferings": [{"InstanceType": "g5.xlarge"}]},
                          {"LocationType": "availability-zone", "Filters": [{"Name": "location", "Values": ["ca-central-1a"]}], "NextToken": "next"})
        result = manager.evaluate(payload)
        assert result["status"] == "blocked"
        assert result["issues"][0]["code"] == "instance_zone"
        assert "ca-central-1a" in result["issues"][0]["message"]
        assert manager.choices(payload)["node"] == ["m6i.large", "g5.xlarge"]
        payload["instances"]["node"]["type"] = "m6i.large"
        assert manager.evaluate(payload)["status"] == "ready"
        stub.assert_no_pending_responses()


@pytest.mark.parametrize("zone", ["us-east-1a", "invalid", [], 123])
def test_invalid_zone_returns_blocker_without_querying_its_offerings(manager, zone):
    payload = {**definition(), "availability_zone": zone}
    with Stubber(manager.ec2):
        assert manager.evaluate(payload)["status"] == "blocked"
        assert manager.choices(payload) == {"node": []}


@pytest.mark.parametrize("zone", [None, ""])
def test_unset_zone_retains_regional_choices(manager, zone):
    with Stubber(manager.ec2):
        payload = {**definition(), "availability_zone": zone}
        assert manager.evaluate(payload)["status"] == "ready"
        assert manager.choices(payload) == manager.choices(definition())


def test_project_validation_rejects_missing_zone_read_permission(manager, mocker):
    del manager.availability_zones
    mocker.patch.object(manager, "regions", return_value=["ca-central-1"])
    with Stubber(manager.ec2) as stub:
        stub.add_client_error("describe_availability_zones", service_error_code="UnauthorizedOperation")
        with pytest.raises(InvalidUsageException, match="describe_availability_zones"):
            manager.validate_project()


def test_catalog_reused_across_requests_but_not_credentials_or_regions(manager, mocker):
    read = mocker.patch.object(manager, "pages", return_value=[{"InstanceType": "m6i.large"}])
    first = manager.catalog("describe_instance_type_offerings", "InstanceTypeOfferings", LocationType="region")
    second = AWSManager(SimpleNamespace(env=ENV), session=manager.session)
    second_read = mocker.patch.object(second, "pages", return_value=[])
    first[0]["InstanceType"] = "modified"
    assert second.catalog("describe_instance_type_offerings", "InstanceTypeOfferings", LocationType="region") == [{"InstanceType": "m6i.large"}]
    read.assert_called_once()
    second_read.assert_not_called()
    for field, value in (("AWS_DEFAULT_REGION", "us-east-1"), ("AWS_SESSION_TOKEN", "new-token"), ("AWS_SECRET_ACCESS_KEY", "rotated")):
        other = AWSManager(SimpleNamespace(env={**ENV, field: value}), session=manager.session)
        other_read = mocker.patch.object(other, "pages", return_value=[])
        assert other.catalog("describe_instance_type_offerings", "InstanceTypeOfferings", LocationType="region") == []
        other_read.assert_called_once()


def test_project_validation_bypasses_warm_catalog(manager, mocker):
    mocker.patch.object(manager, "regions", return_value=["ca-central-1"])
    images = manager.images
    del manager.images
    read = mocker.patch.object(manager, "pages", return_value=images)
    manager.images  # warm shared cache
    del manager.images
    read.side_effect = InvalidUsageException("Permission revoked")
    with pytest.raises(InvalidUsageException, match="Permission revoked"):
        manager.validate_project()


def test_inventory_reads_run_concurrently(manager, mocker):
    del manager.inventory
    barrier = Barrier(4)
    def pages(*args, **kwargs):
        barrier.wait(timeout=5)
        return []
    reads = mocker.patch.object(manager, "pages", side_effect=pages)
    assert manager.inventory == {"instances": [], "volumes": [], "addresses": [], "reservations": []}
    assert reads.call_count == 4


def test_preload_fetches_independent_sources_concurrently(manager, mocker):
    names = ("all_types", "regional_offerings", "quotas_by_name", "inventory", "images", "availability_zones")
    barrier = Barrier(len(names))
    def read(_):
        barrier.wait(timeout=5)
        return []
    for name in names:
        manager.__dict__.pop(name, None)
        mocker.patch.object(AWSManager, name, property(read))
    manager.preload()


def test_all_missing_groups_get_quota_checked_defaults_in_one_response(manager, mocker):
    mocker.patch.object(manager, "preload")
    payload = {"image": "ami-test", "volumes": {}, "instances": {
        "mgmt": {"count": 1, "type": None, "tags": ["mgmt"]},
        "login": {"count": 1, "type": None, "tags": ["login"]},
        "node": {"count": 6, "type": None, "tags": ["node"]},
    }}
    result = manager.editor_resources(payload)
    assert result["instance_defaults"] == {"mgmt": "m6i.large", "login": "m6i.large", "node": "m6i.large"}
    assert result["feasibility"]["status"] == "ready"
    assert payload["instances"]["node"]["type"] is None
    payload["instances"]["node"]["count"] = 100
    result = manager.editor_resources(payload)
    assert "node" not in result["instance_defaults"]
    assert result["feasibility"]["status"] == "blocked"


def test_only_relevant_quota_ids_are_queried_and_values_stay_fresh(manager, mocker):
    expected = {
        ("ec2", "L-1216C47A"): (f"Running On-Demand {STANDARD} instances", 16),
        ("ec2", "L-DB2E81BA"): (f"Running On-Demand {GPU} instances", 8),
        ("ec2", "L-0263D0A3"): ("EC2-VPC Elastic IPs", 5),
        ("ebs", "L-D18FCD1D"): ("Storage for General Purpose SSD (gp2) volumes, in TiB", 1),
    }
    manager.regional_offerings = {"m6i.large", "m6i.xlarge", "g5.xlarge", "mac2.metal"}
    manager.all_types["mac2.metal"] = {}
    def pages(client, operation, key, **params):
        assert operation == "list_service_quotas"
        assert key == "Quotas"
        name, value = expected[params["ServiceCode"], params["QuotaCode"]]
        return [{"QuotaCode": params["QuotaCode"], "QuotaName": name, "Value": value}]
    read = mocker.patch.object(manager, "pages", side_effect=pages)
    del manager.quotas_by_name
    assert manager.quotas_by_name[f"Running On-Demand {STANDARD} instances"] == 16
    assert read.call_count == 4
    assert {(c.kwargs["ServiceCode"], c.kwargs["QuotaCode"]) for c in read.call_args_list} == set(expected)
    expected["ec2", "L-1216C47A"] = (f"Running On-Demand {STANDARD} instances", 32)
    del manager.quotas_by_name
    assert manager.quotas_by_name[f"Running On-Demand {STANDARD} instances"] == 32
    assert read.call_count == 8


def test_targeted_quota_lookup_does_not_treat_missing_values_as_zero(manager, mocker):
    manager.regional_offerings = {"m6i.large"}
    mocker.patch.object(manager, "pages", return_value=[])
    del manager.quotas_by_name
    with pytest.raises(InvalidUsageException, match="did not return the applied quota"):
        manager.quotas_by_name


def test_targeted_quota_filter_is_supported_by_sdk(manager):
    with Stubber(manager.sq) as stub:
        stub.add_response("list_service_quotas", {"Quotas": [
            {"QuotaCode": "L-D18FCD1D", "QuotaName": "gp2", "Value": 1.0},
        ]}, {"ServiceCode": "ebs", "QuotaCode": "L-D18FCD1D"})
        assert manager.pages(manager.sq, "list_service_quotas", "Quotas", ServiceCode="ebs", QuotaCode="L-D18FCD1D")[0]["Value"] == 1


def test_data_volumes_share_root_disk_quota_and_filter_choices(manager):
    payload = definition(2, tags=["nfs", "node"])
    payload["volumes"] = {"nfs": {name: {"size": 100} for name in ("home", "project", "scratch")}}
    assert manager.volume_demand(payload) == ({"gp2": 600}, [])
    assert manager.evaluate(payload)["status"] == "ready"
    manager.budget = {**manager.budget, "gp2": 639}
    result = manager.evaluate(payload)
    issue = next(i for i in result["issues"] if i["code"] == "quota_exceeded")
    assert issue["required"] == 640
    assert issue["available"] == 639
    assert manager.choices(payload)["node"] == []
    manager.budget["gp2"] = 640
    assert manager.choices(payload)["node"]


@pytest.mark.parametrize("volume", [{"size": 0}, {"size": -1}, {"size": 1.5}, {"size": True},
                                    {"size": "100"}, {"size": 100, "type": "gp3"}, None])
def test_invalid_data_volumes_block_feasibility(manager, volume):
    payload = definition(tags=["nfs"])
    payload["volumes"] = {"nfs": {"home": volume}}
    assert any(i["code"] == "volumes" for i in manager.evaluate(payload)["issues"])


def test_data_volume_storage_counted_once_per_matching_instance(manager):
    payload = definition(2, tags=["nfs", "nfs"])
    payload["instances"]["other"] = {"count": 1, "type": "m6i.large", "tags": ["node"]}
    payload["volumes"] = {"nfs": {"home": {"size": 100}}}
    assert manager.volume_demand(payload) == ({"gp2": 200}, [])


@pytest.mark.parametrize("zone", [None, ""])
def test_no_zone_requires_types_in_every_zone(manager, mocker, zone):
    del manager.offered_in_all_zones
    offerings = {"ca-central-1a": {"m6i.large", "m6i.xlarge"},
                 "ca-central-1b": {"m6i.large", "g5.xlarge"}}
    read = mocker.patch.object(manager, "offered_in_zone", side_effect=offerings.__getitem__)
    payload = {**definition(type="m6i.xlarge"), "availability_zone": zone}
    assert manager.choices(payload)["node"] == ["m6i.large"]
    result = manager.evaluate(payload)
    assert result["status"] == "blocked"
    assert "every available zone" in result["issues"][0]["message"]
    assert read.call_count == 2
    assert manager.choices(payload)["node"] == ["m6i.large"]
    assert read.call_count == 2
    payload["availability_zone"] = "ca-central-1a"
    assert manager.evaluate(payload)["status"] == "ready"
    assert manager.choices(payload)["node"] == ["m6i.large", "m6i.xlarge"]


def test_initial_discovery_excludes_types_not_in_all_zones(manager, mocker):
    manager.offered_in_all_zones = {"m6i.large"}
    mocker.patch.object(manager, "preload")
    resources = manager.available_resources
    assert resources["possible_resources"]["types"] == ["m6i.large"]
    # Retain metadata for selections made after choosing a specific zone.
    assert "m6i.xlarge" in {t["name"] for t in resources["resource_details"]["instance_types"]}
    payload = definition(0)
    assert manager.choices(payload)["node"] == ["m6i.large"]


def test_empty_zone_offerings_do_not_fall_back_to_regional_types(manager, mocker):
    del manager.offered_in_all_zones
    mocker.patch.object(manager, "offered_in_zone", side_effect=lambda zone: {"m6i.large"} if zone.endswith("a") else set())
    assert manager.choices(definition())["node"] == []
    assert manager.evaluate(definition())["status"] == "blocked"


def test_failed_zone_discovery_does_not_return_partial_intersection(manager, mocker):
    del manager.offered_in_all_zones
    mocker.patch.object(manager, "offered_in_zone", side_effect=InvalidUsageException("AWS lookup failed"))
    with pytest.raises(InvalidUsageException, match="AWS lookup failed"):
        manager.choices(definition())
    assert "offered_in_all_zones" not in manager.__dict__
