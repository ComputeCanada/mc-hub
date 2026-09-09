import importlib
import json
from decimal import Decimal
from types import SimpleNamespace

import boto3
import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from botocore.stub import Stubber
from sqlalchemy import create_engine, text

from mchub.models.cloud.aws_manager import AWSManager, PRICE_CACHE, PRICE_CONDITION
from mchub.models.cloud.project import Provider
from mchub.resources.project_api import parse_price, ProjectAPI, aws_settings
from mchub.exceptions.invalid_usage_exception import InvalidUsageException
from tests.unit.cloud.test_aws_manager import manager, definition, ENV


@pytest.fixture(autouse=True)
def clean_prices():
    with PRICE_CONDITION:
        PRICE_CACHE.clear()
    yield
    with PRICE_CONDITION:
        PRICE_CACHE.clear()


def test_inclusive_price_ceiling_and_missing_prices(manager):
    manager.project.max_instance_hourly_price = Decimal("0.10")
    manager.types[0]["hourly_price_usd"] = "0.10"
    manager.types[1]["hourly_price_usd"] = "0.1000000001"
    assert manager.choices(definition())["node"] == ["m6i.large"]
    assert manager.evaluate(definition())["status"] == "ready"
    for name in ["m6i.xlarge", "g5.xlarge"]:
        result = manager.evaluate(definition(type=name))
        assert result["status"] == "blocked"
        assert result["issues"][0]["code"] == "instance_price"
    manager.project.max_instance_hourly_price = None
    assert manager.evaluate(definition(type="g5.xlarge"))["status"] == "ready"
    manager.project.max_instance_hourly_price = Decimal("0")
    assert manager.choices(definition())["node"] == []


@pytest.mark.parametrize("value", ["-1", "NaN", "Infinity", True, [], {}, "1e-11", "100000000"])
def test_invalid_limits(value):
    with pytest.raises(InvalidUsageException):
        parse_price(value, Provider.AWS)


def test_price_settings():
    assert parse_price("0", Provider.AWS) == 0
    assert parse_price("", Provider.AWS) is None
    assert parse_price(None, Provider.AWS) is None
    assert parse_price("0.1000000001", Provider.AWS) == Decimal("0.1000000001")
    with pytest.raises(InvalidUsageException):
        parse_price("1", Provider.OPENSTACK)
    p = SimpleNamespace(provider=Provider.AWS, env=ENV, max_instance_hourly_price=Decimal("0.2"))
    assert aws_settings(p)["max_instance_hourly_price"] == "0.2"


def product(rate="0.12", **attributes):
    return json.dumps({"product": {"productFamily": "Compute Instance", "attributes": {
        "regionCode": "ca-central-1", "operatingSystem": "Linux", "tenancy": "Shared",
        "preInstalledSw": "NA", "capacitystatus": "Used", "operation": "RunInstances",
        "instanceType": "m6i.large", **attributes}},
        "terms": {"OnDemand": {"offer": {"priceDimensions": {"rate": {
            "unit": "Hrs", "beginRange": "0", "endRange": "Inf", "pricePerUnit": {"USD": rate}}}}}}})


def test_pricing_pagination_filter_and_cache(mocker):
    session = boto3.Session(aws_access_key_id="test", aws_secret_access_key="secret", region_name="ca-central-1")
    manager = AWSManager(SimpleNamespace(env=ENV), session=session)
    client = session.client("pricing", region_name="us-east-1")
    mocker.patch.object(session, "client", return_value=client)
    filters = {"regionCode": "ca-central-1", "productFamily": "Compute Instance",
               "operatingSystem": "Linux", "tenancy": "Shared", "preInstalledSw": "NA",
               "capacitystatus": "Used", "operation": "RunInstances"}
    params = {"ServiceCode": "AmazonEC2", "MaxResults": 100,
              "Filters": [{"Type": "TERM_MATCH", "Field": k, "Value": v} for k, v in filters.items()]}
    with Stubber(client) as stub:
        stub.add_response("get_products", {"PriceList": [product(), product("0.01", operatingSystem="Windows"),
                          product("0.02", regionCode="us-east-1"), product("0"), product("NaN")], "NextToken": "next"}, params)
        stub.add_response("get_products", {"PriceList": [product("0.13")]}, {**params, "NextToken": "next"})
        assert manager.cached_prices() == {"m6i.large": Decimal("0.13")}
        assert manager.cached_prices() == {"m6i.large": Decimal("0.13")}
        stub.assert_no_pending_responses()


def test_price_cache_isolated_by_region_and_credentials(mocker):
    read = mocker.patch.object(AWSManager, "read_prices", return_value={"m6i.large": Decimal("0.1")})
    for changes in [{}, {}, {"AWS_DEFAULT_REGION": "us-east-1"}, {"AWS_SECRET_ACCESS_KEY": "rotated"}]:
        AWSManager(SimpleNamespace(env={**ENV, **changes})).cached_prices()
    assert read.call_count == 3


def test_validation_checks_pricing_permission_even_with_cache(manager, mocker):
    mocker.patch.object(manager, "regions", return_value=["ca-central-1"])
    manager.cached_prices()
    manager.read_prices.side_effect = InvalidUsageException("pricing:GetProducts denied")
    with pytest.raises(InvalidUsageException, match="pricing:GetProducts"):
        manager.validate_project()


def test_price_column_migration_preserves_projects():
    migration = importlib.import_module("migrations.versions.0007_project_instance_price")
    engine = create_engine("sqlite://")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE project (id INTEGER PRIMARY KEY, name TEXT)"))
        conn.execute(text("INSERT INTO project VALUES (1, 'existing')"))
        with Operations.context(MigrationContext.configure(conn)):
            migration.upgrade()
            assert tuple(conn.execute(text("SELECT name, max_instance_hourly_price FROM project")).one()) == ("existing", None)
            migration.downgrade()
            assert conn.execute(text("SELECT name FROM project")).scalar_one() == "existing"


def test_gpu_metadata_and_price_sorting(manager):
    del manager.types
    base = {"VCpuInfo": {"DefaultVCpus": 4}, "MemoryInfo": {"SizeInMiB": 16384},
            "ProcessorInfo": {"SupportedArchitectures": ["x86_64"]}, "SupportedUsageClasses": ["on-demand"],
            "SupportedRootDeviceTypes": ["ebs"], "SupportedVirtualizationTypes": ["hvm"]}
    manager.all_types = {"g5.xlarge": {**base, "GpuInfo": {"Gpus": [{"Count": 1, "Manufacturer": "NVIDIA",
                         "Name": "A10G", "MemoryInfo": {"SizeInMiB": 24576}}]}}, "m6i.large": base}
    manager.regional_offerings = set(manager.all_types)
    manager.prices = {"g5.xlarge": Decimal("1.006"), "m6i.large": Decimal("0.1")}
    assert [t["name"] for t in manager.types] == ["m6i.large", "g5.xlarge"]
    assert manager.types[0]["gpus"] == []
    assert manager.types[1]["gpus"] == [{"count": 1, "manufacturer": "NVIDIA", "name": "A10G", "memory_mib": 24576}]
    assert manager.types[1]["hourly_price_usd"] == "1.006"


def test_project_price_update_without_credential_or_terraform_changes(mocker):
    from flask import Flask
    project = SimpleNamespace(provider=Provider.AWS, max_instance_hourly_price=None)
    user = SimpleNamespace(projects=[project], is_project_admin=lambda p: True, domain="example.org")
    database = mocker.patch("mchub.resources.project_api.db")
    database.session.get.return_value = project
    terraform = mocker.patch("mchub.resources.project_api.get_terraform_cloud")
    for value, expected in [("0.25", Decimal("0.25")), (None, None)]:
        with Flask(__name__).test_request_context(json={"max_instance_hourly_price": value}):
            ProjectAPI().patch(user, 1)
        assert project.max_instance_hourly_price == expected
    terraform.assert_not_called()
    with Flask(__name__).test_request_context(json={"max_instance_hourly_price": "-1", "agent_pool_name": "new"}):
        with pytest.raises(InvalidUsageException):
            ProjectAPI().patch(user, 1)
    terraform.assert_not_called()


def test_fractional_gpu_uses_logical_count_and_partition_size(manager):
    del manager.types
    manager.all_types = {"g6f.xlarge": {
        "VCpuInfo": {"DefaultVCpus": 4}, "MemoryInfo": {"SizeInMiB": 16384},
        "ProcessorInfo": {"SupportedArchitectures": ["x86_64"]}, "SupportedUsageClasses": ["on-demand"],
        "SupportedRootDeviceTypes": ["ebs"], "SupportedVirtualizationTypes": ["hvm"],
        "GpuInfo": {"Gpus": [{"Count": 0, "LogicalGpuCount": 1, "GpuPartitionSize": 0.125,
            "Manufacturer": "NVIDIA", "Name": "L4", "MemoryInfo": {"SizeInMiB": 2856}}]}}}
    manager.regional_offerings = {"g6f.xlarge"}
    assert manager.types[0]["gpus"] == [{"count": 1, "partition_size": 0.125,
        "manufacturer": "NVIDIA", "name": "L4", "memory_mib": 2856}]
