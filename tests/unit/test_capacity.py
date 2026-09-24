import time
from types import SimpleNamespace

import pytest

from mchub.database import db
from mchub.models.capacity_plan import CapacityPlan
from mchub.models.user import User, UserORM
from mchub.models.magic_castle.magic_castle import MagicCastle
from mchub.models.magic_castle.cluster_status_code import ClusterStatusCode as Status
from mchub.exceptions.invalid_usage_exception import InvalidUsageException
from mchub.services import capacity, capacity_worker as worker
from mchub.resources.capacity_api import CapacityAPI, serialize
from tests.unit.test_usage import app, cluster, config_mock  # noqa: F401


def intention(start, end, count, id=1):
    return SimpleNamespace(starts_at=start, ends_at=end, demand={"vcpus": count}, id=id)


def test_peak_overlap_and_touching_boundaries():
    result = capacity.segments([intention(10, 20, 4), intention(15, 25, 5, 2), intention(25, 30, 8, 3)], {"vcpus": 8}, 10, 30)
    assert [s["demand"]["vcpus"] for s in result] == [4, 9, 5, 8]
    assert [s["shortages"] for s in result] == [{}, {"vcpus": 1}, {}, {}]


def test_unlimited_quota_and_clipped_intervals():
    result = capacity.segments([intention(0, 100, 20)], {"vcpus": None}, 10, 20)
    assert len(result) == 1 and result[0]["shortages"] == {}
    assert result[0]["starts_at"] == capacity.iso(10)
    assert result[0]["ends_at"] == capacity.iso(20)


@pytest.mark.parametrize("start,end", [("bad", "bad"), ("2999-01-01", "2999-02-01"),
    ("2000-01-01T00:00:00Z", "2999-01-01T00:00:00Z"),
    ("2999-01-01T00:00:00Z", "2999-01-01T00:00:00Z")])
def test_invalid_periods(start, end):
    with pytest.raises(InvalidUsageException):
        capacity.parse_period({"starts_at": start, "ends_at": end})


def test_period_normalizes_timezones():
    assert capacity.parse_period({"starts_at": "2999-01-01T03:00:00+03:00", "ends_at": "2999-01-02T00:00:00Z"})[0] == capacity.parse_period({"starts_at": "2999-01-01T00:00:00Z", "ends_at": "2999-01-02T00:00:00Z"})[0]


def test_openstack_demand_includes_root_and_tagged_volumes():
    manager = SimpleNamespace(resource_details={"instance_types": [{"name": "small", "ram": 4096, "vcpus": 2, "required_volume_count": 1, "required_volume_size": 20}]})
    definition = {"instances": {"login": {"count": 2, "type": "small", "tags": ["public", "nfs"]}}, "volumes": {"nfs": {"home": {"size": 50}}}}
    assert capacity.resource_demand(SimpleNamespace(provider="openstack"), definition, manager) == {
        "ram": 8192, "vcpus": 4, "instance_count": 2, "ips": 2, "volume_count": 4, "volume_size": 140, "gpus": 0}
    definition["instances"]["login"]["count"] = -1
    with pytest.raises(InvalidUsageException):
        capacity.resource_demand(SimpleNamespace(provider="openstack"), definition, manager)


@pytest.fixture
def plan(cluster):
    cluster.created_by.projects.append(cluster.project)
    plan = CapacityPlan(project=cluster.project, owner=cluster.created_by, starts_at=time.time()-60,
                        ends_at=time.time()+3600, demand={"vcpus": 4},
                        definition={"cluster_name": "planned", "guest_passwd": "secret", "cloud": {"id": cluster.project_id}},
                        auto_create=True, status="planned")
    db.session.add(plan)
    db.session.commit()
    return plan


def test_project_members_see_demand_but_not_secrets(plan):
    other = UserORM(scoped_id="other@example.org", projects=[plan.project])
    db.session.add(other); db.session.commit()
    user = User(other, "other", "example.org", "saml")
    result = serialize(plan, user, detail=True)
    assert result["demand"] == {"vcpus": 4}
    assert "definition" not in result and not result["can_manage"]
    with pytest.raises(InvalidUsageException):
        CapacityAPI().get(user, plan.project_id, plan.id)
    with pytest.raises(InvalidUsageException):
        CapacityAPI().delete(user, plan.project_id, plan.id)


def test_other_project_is_forbidden(plan):
    other = UserORM(scoped_id="outsider@example.org")
    db.session.add(other); db.session.commit()
    with pytest.raises(InvalidUsageException):
        CapacityAPI().get(User(other, "other", "example.org", "saml"), plan.project_id)


def test_cancel_prevents_start(plan, mocker):
    user = User(plan.owner, "owner", "example.org", "saml")
    CapacityAPI().delete(user, plan.project_id, plan.id)
    create = mocker.patch.object(MagicCastle, "plan_creation")
    worker.start_plan(plan.id)
    assert plan.status == "cancelled"
    create.assert_not_called()


def test_removed_member_cannot_auto_create(plan, mocker):
    plan.owner.projects.clear(); db.session.commit()
    create = mocker.patch.object(MagicCastle, "plan_creation")
    worker.start_plan(plan.id)
    assert plan.status == "failed"
    create.assert_not_called()


def test_start_is_claimed_once_and_links_cluster(plan, cluster, mocker):
    mocker.patch.object(worker, "CloudManager")
    mocker.patch.object(worker, "resource_demand", return_value={"vcpus": 4})
    mocker.patch.object(worker, "budget", return_value={"vcpus": 8})
    mocker.patch.object(worker, "ensure_aws_feasible")
    instance = MagicCastle(cluster)
    factory = mocker.patch.object(worker, "MagicCastle", return_value=instance)
    create = mocker.patch.object(MagicCastle, "plan_creation")
    mocker.patch.object(worker.lifecycle, "validate_apply")
    mocker.patch.object(worker.lifecycle, "claim_background_task")
    apply = mocker.patch.object(worker.lifecycle, "execute_claimed_task")
    worker.start_plan(plan.id)
    worker.start_plan(plan.id)
    assert plan.status == "started" and plan.cluster_usage_id == cluster.usage_id
    factory.assert_called_once(); create.assert_called_once(); apply.assert_called_once()


def test_insufficient_start_quota_does_not_create(plan, mocker):
    mocker.patch.object(worker, "CloudManager")
    mocker.patch.object(worker, "resource_demand", return_value={"vcpus": 4})
    mocker.patch.object(worker, "budget", return_value={"vcpus": 2})
    create = mocker.patch.object(MagicCastle, "plan_creation")
    worker.start_plan(plan.id)
    assert plan.status == "failed"
    create.assert_not_called()


def test_cleanup_uses_lifetime_not_reused_hostname(plan, cluster, mocker):
    plan.cluster_usage_id = "a-different-cluster-lifetime"
    plan.status = "started"; plan.ends_at = time.time()-1; db.session.commit()
    destroy = mocker.patch.object(worker.lifecycle, "plan_teardown")
    worker.end_plan(plan.id)
    assert plan.status == "ended"
    destroy.assert_not_called()


def test_cleanup_applies_only_exact_destroy_run(plan, cluster, mocker):
    plan.cluster_usage_id = cluster.usage_id; plan.status = "started"; plan.ends_at = time.time()-1
    cluster.undeployed = False; cluster.status = Status.PROVISIONING_SUCCESS
    db.session.commit()
    mocker.patch.object(MagicCastle, "_update_status_from_tf_cloud")
    def teardown(*args):
        cluster.status = Status.CREATED
        cluster.tfcloud_run.run_id = "destroy-plan"
        cluster.tfcloud_run.plan = {"resource_changes": []}
        db.session.commit()
    mocker.patch.object(worker.lifecycle, "plan_teardown", side_effect=teardown)
    tf = mocker.Mock(); tf.get_run_status.return_value = (None, True)
    mocker.patch.object(worker.lifecycle, "get_terraform_cloud", return_value=tf)
    mocker.patch("mchub.services.terraform_cloud_api.get_terraform_cloud", return_value=tf)
    apply = mocker.patch.object(MagicCastle, "apply")
    worker.end_plan(plan.id)
    apply.assert_called_once_with(initiated_by=None)
    tf.get_run_status.assert_called_with("destroy-plan")
    assert plan.status == "cleanup_pending"  # Await cloud confirmation.


def test_restart_does_not_retry_start(plan, mocker):
    plan.status = "starting"; db.session.commit()
    worker.recover_interrupted()
    create = mocker.patch.object(MagicCastle, "plan_creation")
    worker.start_plan(plan.id)
    assert plan.status == "failed"
    create.assert_not_called()


@pytest.mark.parametrize("provider", ["openstack", "aws"])
def test_forecast_excludes_cancelled_and_accounts_for_deployed_plans(plan, cluster, mocker, provider):
    plan.project.provider = provider
    db.session.commit()
    mocker.patch.object(capacity, "CloudManager")
    mocker.patch.object(capacity, "planning_budget", return_value={"vcpus": 8})
    report = capacity.forecast(plan.project, time.time(), plan.ends_at)
    assert report["segments"][0]["demand"] == {"vcpus": 4, "gpus": 0}
    plan.cluster_usage_id = cluster.usage_id
    cluster.undeployed = False; cluster.status = Status.BUILD_RUNNING
    db.session.commit()
    assert capacity.forecast(plan.project, time.time(), plan.ends_at)["segments"][0]["demand"] == {"vcpus": 4, "gpus": 0}
    cluster.status = Status.PROVISIONING_SUCCESS; db.session.commit()
    expected = {"vcpus": 4, "gpus": 0} if provider == "openstack" else {"gpus": 0}
    report = capacity.forecast(plan.project, time.time(), plan.ends_at)
    assert report["segments"][0]["demand"] == expected
    assert report["quota_basis"] == ("project_total" if provider == "openstack" else "currently_available")
    plan.cluster_usage_id = None; plan.status = "cancelled"; db.session.commit()
    assert capacity.forecast(plan.project, time.time(), plan.ends_at)["segments"][0]["demand"] == {}


def test_save_allows_conflicts_and_does_not_create_cluster(plan, app, mocker):
    from mchub.resources import capacity_api as api
    mocker.patch.object(api, "MagicCastleConfiguration")
    mocker.patch.object(MagicCastle, "validate_creation_version")
    create = mocker.patch.object(MagicCastle, "plan_creation")
    mocker.patch.object(api, "resource_demand", return_value={"vcpus": 4})
    mocker.patch.object(api, "forecast", return_value={"segments": [{"shortages": {"vcpus": 2}}]})
    user = User(plan.owner, "owner", "example.org", "saml")
    payload = {"definition": plan.definition, "starts_at": capacity.iso(time.time()+100),
               "ends_at": capacity.iso(time.time()+200), "auto_create": False}
    with app.test_request_context(json=payload):
        result, code = api.CapacityAPI().post(user, plan.project_id)
    assert code == 201 and result["forecast"]["segments"][0]["shortages"]
    saved = db.session.get(CapacityPlan, result["plan"]["id"])
    assert saved.owner_id == user.orm.id and saved.definition["expiration_date"] is None
    create.assert_not_called()


def test_quota_outage_keeps_plans_visible(plan, mocker):
    mocker.patch("mchub.resources.capacity_api.forecast", side_effect=RuntimeError("private cloud credentials"))
    result = CapacityAPI().get(User(plan.owner, "owner", "example.org", "saml"), plan.project_id)
    assert result["plans"][0]["id"] == plan.id and result["forecast"] is None
    assert "private cloud credentials" not in result["warning"]


def test_cleanup_busy_cluster_retries_without_applying(plan, cluster, mocker):
    plan.status = "started"; plan.cluster_usage_id = cluster.usage_id; plan.ends_at = time.time()-1
    cluster.status = Status.BUILD_RUNNING; cluster.undeployed = False
    db.session.commit()
    mocker.patch.object(MagicCastle, "_update_status_from_tf_cloud")
    apply = mocker.patch.object(worker.lifecycle, "apply_cluster")
    worker.end_plan(plan.id)
    assert plan.status == "cleanup_pending"
    apply.assert_not_called()


def test_expired_period_cannot_apply_a_build(plan, cluster, mocker):
    plan.cluster_usage_id = cluster.usage_id; plan.ends_at = time.time()-1; db.session.commit()
    tf = mocker.Mock(); tf.get_run_status.return_value = (None, False)
    mocker.patch("mchub.services.terraform_cloud_api.get_terraform_cloud", return_value=tf)
    with pytest.raises(InvalidUsageException):
        capacity.validate_plan_apply(cluster)
    tf.get_run_status.return_value = (None, True)
    capacity.validate_plan_apply(cluster)


def test_migration_round_trip():
    import importlib
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import create_engine, inspect
    migration = importlib.import_module("migrations.versions.0021_capacity_planner")
    with create_engine("sqlite://").begin() as connection:
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
            assert "capacity_plan" in inspect(connection).get_table_names()
            migration.downgrade()
            assert "capacity_plan" not in inspect(connection).get_table_names()


def test_manual_creation_links_once_and_keeps_end_cleanup(plan, app, mocker):
    from mchub.resources.magic_castle_api import MagicCastleAPI
    plan.auto_create = False; db.session.commit()
    mocker.patch.object(MagicCastle, "validate_creation_version")
    mocker.patch.object(capacity, "resource_demand", return_value={"vcpus": 4})
    background = mocker.patch.object(MagicCastleAPI, "_run_in_background")
    create = mocker.patch.object(MagicCastle, "plan_creation")
    user = User(plan.owner, "owner", "example.org", "saml")
    payload = {**plan.definition, "capacity_plan_id": plan.id, "expiration_date": "2999-01-01"}
    with app.test_request_context(json=payload):
        assert MagicCastleAPI().post(user, None)[1] == 202
    assert plan.status == "manual_starting" and plan.cluster_usage_id is not None
    background.call_args.args[1]()  # Execute the accepted background task.
    assert plan.status == "manual_ready"
    assert create.call_args.args[0]["expiration_date"] is None
    assert create.call_args.args[1] == plan.owner_id
    with app.test_request_context(json=payload), pytest.raises(InvalidUsageException):
        MagicCastleAPI().post(user, None)
    background.assert_called_once()


def test_started_plan_cannot_cancel_cleanup(plan):
    plan.cluster_usage_id = "linked"; plan.status = "failed"; db.session.commit()
    user = User(plan.owner, "owner", "example.org", "saml")
    with pytest.raises(InvalidUsageException):
        CapacityAPI().delete(user, plan.project_id, plan.id)
    assert not serialize(plan, user)["can_cancel"]


def test_interrupted_start_without_a_remote_run_is_not_left_busy(plan, cluster):
    plan.status = "starting"; plan.cluster_usage_id = cluster.usage_id
    cluster.status = Status.PLAN_RUNNING; cluster.tfcloud_run.run_id = None
    db.session.commit()
    worker.recover_interrupted()
    assert plan.status == "failed" and cluster.status == Status.PLAN_ERROR


def test_openstack_planning_uses_total_quota_while_launch_checks_available():
    from mchub.models.cloud.openstack_manager import OpenStackManager
    manager = SimpleNamespace(
        compute_quotas={"instances": {"limit": 20, "in_use": 19},
                        "ram": {"limit": 65536, "in_use": 60000},
                        "cores": {"limit": 32, "in_use": 30}},
        volume_quotas={"volumes": {"limit": 40, "in_use": 35},
                       "gigabytes": {"limit": 1000, "in_use": 900}},
        network_quotas={"floatingip": {"limit": -1, "used": 2}},
        quotas={"instance_count": {"max": 1}, "ram": {"max": 5536}, "vcpus": {"max": 2},
                "volume_count": {"max": 5}, "volume_size": {"max": 100}, "ips": {"max": -3}},
    )
    manager.total_quotas = OpenStackManager.total_quotas.fget(manager)
    project = SimpleNamespace(provider="openstack")
    limits = capacity.planning_budget(project, manager)
    assert limits == {"instance_count": 20, "ram": 65536, "vcpus": 32,
                      "volume_count": 40, "volume_size": 1000, "ips": None}
    assert capacity.budget(project, manager)["vcpus"] == 2
    assert capacity.budget(project, manager)["ips"] is None
    plans = [intention(10, 20, 24), intention(15, 25, 16, 2)]
    forecast = capacity.segments(plans, limits, 10, 25)
    assert [segment["shortages"] for segment in forecast] == [{}, {"vcpus": 8}, {}]


@pytest.mark.parametrize("details,expected", [
    ({"name": "g4-24gb-32"}, 4),
    ({"name": "gpu12-120-850gb-a100x1"}, 1),
    ({"name": "c8-32gb"}, 0),
    ({"name": "p4d.24xlarge", "gpus": [{"count": 8}]}, 8),
    ({"name": "g6f.large", "gpus": [{"count": 1, "partition_size": 0.125}]}, 0.125),
    ({"name": "custom", "gpus": 2}, 2),
])
def test_gpu_counts_from_metadata_and_flavor_names(details, expected):
    assert capacity.gpu_count(details) == expected


def test_gpu_demand_multiplies_each_instance_group():
    definition = {"instances": {
        "gpu": {"count": 3, "type": "g2-24gb-32"},
        "cpu": {"count": 5, "type": "c8-32gb"},
    }}
    manager = SimpleNamespace(resource_details={"instance_types": [
        {"name": "g2-24gb-32"}, {"name": "c8-32gb"}]})
    assert capacity.gpu_demand(SimpleNamespace(provider="openstack"), definition, manager) == 6


@pytest.mark.parametrize("provider", ["openstack", "aws"])
def test_gpu_forecast_includes_deployed_legacy_plans_without_gpu_quota(plan, cluster, mocker, provider):
    plan.project.provider = provider
    plan.definition = {"instances": {"node": {"type": "gpu-type", "count": 3}}}
    plan.cluster_usage_id = cluster.usage_id
    cluster.status = Status.PROVISIONING_SUCCESS; cluster.undeployed = False
    db.session.commit()
    manager = SimpleNamespace(types_by_name={"gpu-type": {"gpus": [{"count": 2}]}},
                              resource_details={"instance_types": [{"name": "gpu-type", "gpus": 2}]})
    mocker.patch.object(capacity, "CloudManager", return_value=SimpleNamespace(manager=manager))
    mocker.patch.object(capacity, "planning_budget", return_value={"vcpus": 8})
    candidate = intention(time.time(), plan.ends_at, 1, None)
    candidate.demand["gpus"] = 4
    report = capacity.forecast(plan.project, time.time(), plan.ends_at, candidate)
    assert report["plan_gpu_counts"][plan.id] == 6
    assert report["segments"][0]["demand"]["gpus"] == 10
    assert report["segments"][0]["shortages"] == {}
    assert "gpus" not in plan.demand  # Read-only enrichment.


def test_edit_replaces_plan_and_preserves_owner(plan, app, mocker):
    from mchub.resources import capacity_api as api
    mocker.patch.object(api, "MagicCastleConfiguration")
    mocker.patch.object(MagicCastle, "validate_creation_version")
    mocker.patch.object(api, "resource_demand", return_value={"vcpus": 8, "gpus": 2})
    forecast = mocker.patch.object(api, "forecast", return_value={"segments": []})
    admin = UserORM(scoped_id="admin@example.org")
    plan.project.admins.append(admin); db.session.commit()
    owner_id = plan.owner_id
    payload = {"definition": {"cluster_name": "updated"}, "starts_at": capacity.iso(time.time()+1000),
               "ends_at": capacity.iso(time.time()+2000), "auto_create": False}
    user = User(admin, "admin", "example.org", "saml")
    with app.test_request_context(json=payload):
        api.CapacityAPI().post(user, plan.project_id, plan.id, preview=True)
    assert plan.definition["cluster_name"] == "planned"
    assert forecast.call_args.kwargs["exclude_plan_id"] == plan.id
    with app.test_request_context(json=payload):
        result, status = api.CapacityAPI().put(user, plan.project_id, plan.id)
    assert status == 200 and result["plan"]["id"] == plan.id
    assert plan.owner_id == owner_id and plan.definition["cluster_name"] == "updated"
    assert plan.demand == {"vcpus": 8, "gpus": 2} and not plan.auto_create
    assert db.session.scalar(db.select(db.func.count()).select_from(CapacityPlan)) == 1


@pytest.mark.parametrize("status", ["starting", "started", "manual_starting", "cancelled"])
def test_edit_rejects_plans_already_claimed_or_cancelled(plan, app, status):
    plan.status = status; db.session.commit()
    user = User(plan.owner, "owner", "example.org", "saml")
    with app.test_request_context(json={}), pytest.raises(InvalidUsageException) as err:
        CapacityAPI().put(user, plan.project_id, plan.id)
    assert err.value.status_code == 409


def test_edit_forbidden_for_other_member(plan, app):
    other = UserORM(scoped_id="member@example.org", projects=[plan.project])
    db.session.add(other); db.session.commit()
    with app.test_request_context(json={}), pytest.raises(InvalidUsageException) as err:
        CapacityAPI().put(User(other, "member", "example.org", "saml"), plan.project_id, plan.id)
    assert err.value.status_code == 403


def test_edit_forecast_counts_replacement_once(plan, mocker):
    mocker.patch.object(capacity, "CloudManager")
    mocker.patch.object(capacity, "planning_budget", return_value={"vcpus": 8})
    candidate = intention(plan.starts_at, plan.ends_at, 6, None)
    report = capacity.forecast(plan.project, time.time(), plan.ends_at, candidate, exclude_plan_id=plan.id)
    assert report["segments"][0]["demand"] == {"vcpus": 6}
    assert report["segments"][0]["shortages"] == {}


@pytest.mark.parametrize("remaining", [3600, 45 * 86400, -1])
def test_dashboard_forecast_stops_at_latest_plan_end(plan, mocker, remaining):
    plan.ends_at = time.time() + remaining
    plan.status = "failed" if remaining < 0 else "planned"
    db.session.commit()
    mocker.patch.object(capacity, "CloudManager")
    mocker.patch.object(capacity, "planning_budget", return_value={"vcpus": 8})
    result = CapacityAPI().get(User(plan.owner, "owner", "example.org", "saml"), plan.project_id)
    segments = result["forecast"]["segments"]
    if remaining > 0:
        assert segments[-1]["ends_at"] == capacity.iso(plan.ends_at)
    else:
        assert segments == []


def test_dashboard_has_no_forecast_periods_without_plans(plan, mocker):
    plan.status = "cancelled"
    db.session.commit()
    mocker.patch.object(capacity, "CloudManager")
    mocker.patch.object(capacity, "planning_budget", return_value={"vcpus": 8})
    result = CapacityAPI().get(User(plan.owner, "owner", "example.org", "saml"), plan.project_id)
    assert result["plans"] == []
    assert result["forecast"]["segments"] == []


@pytest.mark.parametrize("start_offset", [-3600, 86400])
def test_dashboard_forecast_starts_at_earliest_plan(plan, mocker, start_offset):
    plan.starts_at = time.time() + start_offset
    plan.ends_at = time.time() + 3 * 86400
    later = CapacityPlan(project=plan.project, owner=plan.owner, definition=plan.definition,
                         demand={"vcpus": 2}, starts_at=plan.starts_at + 86400,
                         ends_at=plan.ends_at + 86400, auto_create=False, status="planned")
    db.session.add(later)
    db.session.commit()
    mocker.patch.object(capacity, "CloudManager")
    mocker.patch.object(capacity, "planning_budget", return_value={"vcpus": 8})
    result = CapacityAPI().get(User(plan.owner, "owner", "example.org", "saml"), plan.project_id)
    segments = result["forecast"]["segments"]
    assert segments[0]["starts_at"] == capacity.iso(plan.starts_at)
    assert segments[-1]["ends_at"] == capacity.iso(later.ends_at)
