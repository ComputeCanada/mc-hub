from copy import deepcopy
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import PropertyMock
import importlib

import pytest
from freezegun import freeze_time
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text

from mchub.database import db
from mchub.models.benchmark import Benchmark, BenchmarkRun
from mchub.models.magic_castle.magic_castle import MagicCastle, MagicCastleORM
from mchub.models.magic_castle.cluster_status_code import ClusterStatusCode as Status
from mchub.models.magic_castle.magic_castle_configuration import MagicCastleConfiguration, validate_cluster_name
from mchub.models.magic_castle.terraform_cloud_status import TFCloudStatusCode as TFStatus
from mchub.models.terraform_cloud import TerraformCloudRunORM
from mchub.models.usage import utcnow
from mchub.services import benchmark_runner as runner, benchmarks, usage, cluster_lifecycle
import mchub.models.magic_castle.magic_castle as mc_module
from mchub.exceptions.invalid_usage_exception import InvalidUsageException
from mchub.resources.usage_api import UsageAPI
from tests.unit.test_usage import app, cluster, config_mock  # noqa: F401
from tests.data import NON_EXISTING_CLUSTER_CONFIGURATION, ALICE_HEADERS

OWNER_HEADERS = {**ALICE_HEADERS, "eduPersonPrincipalName": "owner@example.org"}


@pytest.fixture(autouse=True)
def setup_backends(mocker, tmp_path):
    mocker.patch.object(benchmarks, "DATABASE_PATH", str(tmp_path))
    tf = mocker.patch.object(mc_module, "get_terraform_cloud").return_value
    mocker.patch.object(benchmarks, "get_terraform_cloud", return_value=tf)
    tf.create_workspace.side_effect = lambda name, *_: f"ws-{name}"
    tf.get_run_status.return_value = (None, False)
    tf.plan_from_commit.return_value = None
    storage = mocker.patch.object(mc_module, "get_github_storage").return_value
    storage.create_repo.side_effect = lambda hostname, *_: f"org/{hostname}"
    storage.write.return_value = "initial-sha"
    storage.trigger_run.return_value = True
    mocker.patch.object(mc_module.DnsManager, "get_environment_variables", return_value={})
    return storage, tf


@pytest.fixture
def benchmark(cluster, mocker):
    cluster.project.admins.append(cluster.created_by)
    cluster.project.env = {}
    cluster.created_by.projects.append(cluster.project)
    db.session.commit()
    mocker.patch.object(MagicCastle, "validate_creation_version")
    benchmark = Benchmark(project_id=cluster.project.id, project_key=cluster.project.usage_id,
        name="Standard cluster", configuration={**deepcopy(NON_EXISTING_CLUSTER_CONFIGURATION), "cloud": {"id": cluster.project.id}},
        frequency="hourly", timeout_minutes=120, enabled=True, setup_status="ready",
        next_run_at=utcnow(), created_by=cluster.created_by.scoped_id)
    db.session.add(benchmark)
    db.session.commit()
    return benchmark


def payload(benchmark):
    return {"project_id": benchmark.project_id, "name": benchmark.name,
            "configuration": benchmark.configuration, "frequency": "daily", "enabled": True, "timeout_minutes": 120}


def test_project_admin_authorization_and_input_validation(app, benchmark):
    client = app.test_client()
    assert client.get(f"/api/benchmarks/{benchmark.id}", headers=ALICE_HEADERS).status_code == 403
    assert client.post("/api/benchmarks", json=payload(benchmark), headers=ALICE_HEADERS).status_code == 403
    assert client.get("/api/benchmarks", headers=ALICE_HEADERS).status_code == 403
    assert client.get(f"/api/benchmarks/{benchmark.id}", headers=OWNER_HEADERS).status_code == 200
    valid = payload(benchmark)
    for change in ({"frequency": "minutely"}, {"timeout_minutes": 0}, {"enabled": "yes"}, {"name": ""}, {"configuration": {}},
                   {"success_criterion": "planned"}, {"success_criterion": None}, {"success_criterion": []}):
        assert client.post("/api/benchmarks", json={**valid, **change}, headers=OWNER_HEADERS).status_code == 400
    result = client.post("/api/benchmarks", json=valid, headers=OWNER_HEADERS)
    assert result.status_code == 201
    assert result.get_json()["success_criterion"] == "healthy"
    assert result.get_json()["configuration"]["cloud"]["id"] == benchmark.project_id
    valid = deepcopy(valid)
    valid["configuration"]["cluster_name"] = "build-benchmark"
    result = client.post("/api/benchmarks", json={**valid, "success_criterion": "build_completed"}, headers=OWNER_HEADERS)
    assert result.status_code == 201
    assert result.get_json()["success_criterion"] == "build_completed"


def test_first_save_prepares_integrations_without_deploying_or_counting_a_run(app, benchmark, setup_backends, mocker):
    from mchub.models.usage import UsageLifetime
    from mchub.resources.magic_castle_api import MagicCastleAPI
    storage, tf = setup_backends
    plan = mocker.patch.object(MagicCastle, "create_plan")
    apply = mocker.patch.object(MagicCastle, "apply")
    client = app.test_client()
    data = deepcopy(payload(benchmark))
    data["enabled"] = False
    data["configuration"]["public_keys"] = []
    data["configuration"]["hieradata_entries"] = [
        {"key": "profile::test", "value": "puppet-value", "encrypt": False},
        {"key": "profile::secret", "value": "puppet-secret", "encrypt": True},
    ]
    response = client.post("/api/benchmarks", json=data, headers=OWNER_HEADERS)
    assert response.status_code == 201
    saved = response.get_json()
    assert saved["setup_status"] == "ready"
    assert saved["identity_locked"] is True
    owned = benchmarks.reusable_cluster(saved["id"])
    assert owned.benchmark_id == saved["id"]
    assert owned.benchmark_run_id is None
    assert owned.status == Status.NOT_DEPLOYED
    assert owned.undeployed
    assert owned.tfcloud_run.run_id is None
    storage.create_repo.assert_called_once()
    tf.create_workspace.assert_called_once_with(data["configuration"]["cluster_name"], owned.usage_repository, "p-1")
    tf.set_workspace_variable_set.assert_called_once()
    assert storage.write.call_args.kwargs == {"trigger_run": False}
    variables = storage.write.call_args.args[0]
    assert variables["public_keys"] == []
    assert "puppet-value" in variables["hieradata"]
    assert "ENC[PKCS7," in variables["hieradata"]
    assert "puppet-secret" not in variables["hieradata"]
    plan.assert_not_called()
    apply.assert_not_called()
    assert db.session.scalar(db.select(BenchmarkRun)) is None
    assert db.session.scalar(db.select(UsageLifetime)) is None
    assert MagicCastleAPI().get(SimpleNamespace(magic_castles=[MagicCastle(owned)]), None) == []
    with pytest.raises(InvalidUsageException, match="managed by its benchmark"):
        cluster_lifecycle.claim_background_task(owned)
    # Editing the ready definition preserves the prepared integrations.
    assert client.put(f"/api/benchmarks/{saved['id']}", json=data, headers=OWNER_HEADERS).status_code == 200
    storage.create_repo.assert_called_once()
    tf.create_workspace.assert_called_once()
    storage.write.assert_called_once()


@pytest.mark.parametrize("failure_stage", ["workspace", "variables"])
def test_failed_first_save_returns_id_and_retries_existing_integrations(app, benchmark, setup_backends, failure_stage):
    storage, tf = setup_backends
    failed = tf.create_workspace if failure_stage == "workspace" else storage.write
    original = failed.side_effect
    failed.side_effect = RuntimeError("remote secret must not be returned")
    client = app.test_client()
    response = client.post("/api/benchmarks", json=payload(benchmark), headers=OWNER_HEADERS)
    assert response.status_code == 502
    saved = response.get_json()["benchmark"]
    assert saved["setup_status"] == "failed"
    assert saved["identity_locked"] is True
    assert "remote secret" not in response.get_data(as_text=True)
    owned = benchmarks.reusable_cluster(saved["id"])
    owned_id = owned.id
    assert owned.usage_repository is not None
    assert client.post(f"/api/benchmarks/{saved['id']}/run", headers=OWNER_HEADERS).status_code == 409
    failed.side_effect = original
    response = client.put(f"/api/benchmarks/{saved['id']}", json=payload(benchmark), headers=OWNER_HEADERS)
    assert response.status_code == 200
    assert response.get_json()["setup_status"] == "ready"
    assert response.get_json()["setup_error"] is None
    assert benchmarks.reusable_cluster(saved["id"]).id == owned_id
    storage.create_repo.assert_called_once()
    assert tf.create_workspace.call_count == (2 if failure_stage == "workspace" else 1)
    assert db.session.scalar(db.select(BenchmarkRun)) is None


@pytest.mark.parametrize("setup_status", ["pending", "creating", "failed"])
def test_incomplete_setup_blocks_scheduled_and_manual_runs(benchmark, setup_status):
    benchmark.setup_status = setup_status
    db.session.commit()
    benchmarks.schedule_due()
    assert db.session.scalar(db.select(BenchmarkRun)) is None
    with pytest.raises(InvalidUsageException, match="Save the benchmark"):
        benchmarks.enqueue(benchmark)


def test_busy_setup_blocks_edits_and_archive(app, benchmark):
    client = app.test_client()
    with benchmarks.benchmark_lock(benchmark.id):
        for method, kwargs in [(client.put, {"json": payload(benchmark)}), (client.delete, {})]:
            response = method(f"/api/benchmarks/{benchmark.id}", headers=OWNER_HEADERS, **kwargs)
            assert response.status_code == 409
        with pytest.raises(InvalidUsageException, match="busy"):
            benchmarks.enqueue(benchmark)


def test_archive_before_first_run_cleans_integrations_without_creating_results(app, benchmark, setup_backends):
    storage, tf = setup_backends
    client = app.test_client()
    saved = client.post("/api/benchmarks", json=payload(benchmark), headers=OWNER_HEADERS).get_json()
    owned = benchmarks.reusable_cluster(saved["id"])
    workspace, hostname = owned.tfcloud_workspace, owned.hostname
    assert client.delete(f"/api/benchmarks/{saved['id']}", headers=OWNER_HEADERS).status_code == 204
    assert db.session.get(Benchmark, saved["id"]).archived
    assert benchmarks.reusable_cluster(saved["id"]) is None
    assert db.session.scalar(db.select(BenchmarkRun)) is None
    storage.archive_repo.assert_called_once_with(hostname)
    tf.verify_workspace_empty.assert_called_with(workspace)
    tf.lock_workspace.assert_called_once_with(workspace)


def test_snapshots_nonoverlap_archive_and_history(app, benchmark):
    client = app.test_client()
    first = client.post(f"/api/benchmarks/{benchmark.id}/run", headers=OWNER_HEADERS)
    assert first.status_code == 202
    run = db.session.get(BenchmarkRun, first.get_json()["id"])
    original_count = run.configuration["instances"]["node"]["count"]
    assert run.hostname == f"{benchmark.configuration['cluster_name']}.{benchmark.configuration['domain']}"
    assert client.post(f"/api/benchmarks/{benchmark.id}/run", headers=OWNER_HEADERS).status_code == 409
    update = deepcopy(payload(benchmark))
    update["configuration"]["instances"]["node"]["count"] = 2
    update["success_criterion"] = "build_completed"
    assert client.put(f"/api/benchmarks/{benchmark.id}", json=update, headers=OWNER_HEADERS).status_code == 200
    assert run.configuration["instances"]["node"]["count"] == original_count
    assert run.revision == 1
    assert run.success_criterion == "healthy"
    assert benchmark.success_criterion == "build_completed"
    assert client.delete(f"/api/benchmarks/{benchmark.id}", headers=OWNER_HEADERS).status_code == 204
    assert client.post(f"/api/benchmarks/{benchmark.id}/run", headers=OWNER_HEADERS).status_code == 409
    result = client.get(f"/api/benchmarks/{benchmark.id}", headers=OWNER_HEADERS).get_json()
    assert result["total_runs"] == 1
    assert "guest_passwd" not in result["runs"][0]["configuration"]
    runner.advance_run(run.id)
    assert run.outcome == "cancelled"
    runner.advance_run(run.id)
    assert run.phase == "complete"


@pytest.mark.parametrize("name,domain", [
    ("benchmark", "example.org"),
    ("abcdefghijklmnopqrstuvw", "subdomain.example.org"),
    ("benchmark", "a" * 28 + ".example.org"),
    ("benchmark-long-name", "a" * 19 + ".example.org"),
])
def test_runs_use_exact_same_configured_name(benchmark, name, domain):
    benchmark.configuration = {**benchmark.configuration, "cluster_name": name, "domain": domain}
    run = benchmarks.enqueue(benchmark)
    assert run.configuration["cluster_name"] == name
    assert len(f"{name}.int.{domain}") <= 63
    validate_cluster_name(name)
    assert run.hostname == f"{name}.{domain}"
    assert benchmark.configuration["cluster_name"] == name
    run.phase, run.active_benchmark_id = "complete", None
    db.session.commit()
    next_run = benchmarks.enqueue(benchmark)
    assert next_run.id != run.id
    assert next_run.hostname == run.hostname
    assert len(f"{next_run.configuration['cluster_name']}.int.{domain}") <= 63


def test_domain_length_validation_on_save_and_enqueue(app, benchmark, mocker):
    longest_domain = "a" * 28 + ".example.org"
    too_long_domain = "a" + longest_domain
    mocker.patch("mchub.models.magic_castle.magic_castle_configuration.DnsManager.get_available_domains",
                 return_value=[longest_domain, too_long_domain])
    from mchub.configuration import get_config
    get_config()["domains"] = {**get_config()["domains"], longest_domain: {"dns_provider": "cf1"}}
    data = deepcopy(payload(benchmark))
    data["configuration"]["cluster_name"] = "b" * 18
    data["configuration"]["domain"] = longest_domain
    client = app.test_client()
    saved = client.post("/api/benchmarks", json=data, headers=OWNER_HEADERS)
    assert saved.status_code == 201
    run_response = client.post(f"/api/benchmarks/{saved.get_json()['id']}/run", headers=OWNER_HEADERS)
    assert run_response.status_code == 202
    run = db.session.get(BenchmarkRun, run_response.get_json()["id"])
    assert len(f"{run.configuration['cluster_name']}.int.{longest_domain}") == 63
    data["configuration"]["domain"] = too_long_domain
    for method, url in [(client.post, "/api/benchmarks"), (client.put, f"/api/benchmarks/{benchmark.id}")]:
        rejected = method(url, json=data, headers=OWNER_HEADERS)
        assert rejected.status_code == 400
        assert "at most 63 characters" in rejected.get_json()["message"]
    # Previously saved definitions must also be checked before allocating a run.
    benchmark.configuration = data["configuration"]
    with pytest.raises(InvalidUsageException, match="at most 63 characters"):
        benchmarks.enqueue(benchmark)
    assert db.session.scalar(db.select(BenchmarkRun).filter_by(benchmark_id=benchmark.id)) is None


def test_names_are_reserved_and_identity_is_fixed_after_first_save(app, benchmark, cluster, mocker):
    client = app.test_client()
    saved = client.put(f"/api/benchmarks/{benchmark.id}", json=payload(benchmark), headers=OWNER_HEADERS)
    assert saved.status_code == 200
    assert saved.get_json()["identity_locked"] is True
    assert client.post("/api/benchmarks", json=payload(benchmark), headers=OWNER_HEADERS).status_code == 409
    # The same workspace name also conflicts across different DNS domains.
    data = deepcopy(payload(benchmark))
    data["configuration"]["domain"] = "another.example.org"
    mocker.patch("mchub.models.magic_castle.magic_castle_configuration.DnsManager.get_available_domains",
                 return_value=[benchmark.configuration["domain"], data["configuration"]["domain"]])
    assert client.post("/api/benchmarks", json=data, headers=OWNER_HEADERS).status_code == 409
    with pytest.raises(InvalidUsageException, match="reserved by a benchmark"):
        MagicCastle().plan_creation(deepcopy(benchmark.configuration))
    run = benchmarks.enqueue(benchmark)
    db.session.commit()
    assert client.get(f"/api/benchmarks/{benchmark.id}", headers=OWNER_HEADERS).get_json()["benchmark"]["identity_locked"] is True
    for key, value in [("cluster_name", "renamed"), ("domain", "another.example.org")]:
        data = deepcopy(payload(benchmark))
        data["configuration"][key] = value
        rejected = client.put(f"/api/benchmarks/{benchmark.id}", json=data, headers=OWNER_HEADERS)
        assert rejected.status_code == 400
        assert "Keep the cluster name and domain" in rejected.get_json()["message"]
    # A normal cluster also reserves its workspace name.
    data = deepcopy(payload(benchmark))
    data["configuration"]["cluster_name"] = cluster.hostname.split(".")[0]
    assert client.post("/api/benchmarks", json=data, headers=OWNER_HEADERS).status_code == 409
    assert run.configuration["cluster_name"] == benchmark.configuration["cluster_name"]


@pytest.mark.parametrize("queued", [False, True])
def test_archive_cleans_retained_integrations_even_with_queued_run(app, benchmark, cluster, mocker, queued):
    run = benchmarks.enqueue(benchmark)
    cluster.benchmark_run_id = run.id
    cluster.hostname = run.hostname
    cluster.status = Status.NOT_DEPLOYED
    cluster.undeployed = True
    run.phase, run.active_benchmark_id = "complete", None
    run.outcome, run.cleanup_at = "successful", utcnow()
    db.session.commit()
    cleanup_run = benchmarks.enqueue(benchmark) if queued else run
    db.session.commit()
    mocker.patch.object(MagicCastle, "_update_status_from_tf_cloud")
    mocker.patch.object(runner, "get_terraform_cloud").return_value.get_run_plan_log_json.return_value = {"resource_changes": []}
    def destroy(self):
        db.session.delete(self.orm)
        db.session.commit()
    destroy_mock = mocker.patch.object(MagicCastle, "destroy_empty_cluster", autospec=True, side_effect=destroy)
    assert app.test_client().delete(f"/api/benchmarks/{benchmark.id}", headers=OWNER_HEADERS).status_code == 204
    assert cleanup_run.active_benchmark_id == benchmark.id
    runner.advance_run(cleanup_run.id)
    if queued:
        assert cleanup_run.outcome == "cancelled"
        runner.advance_run(cleanup_run.id)
    assert cleanup_run.phase == "complete"
    assert cleanup_run.cleanup_at is not None
    assert run.outcome == "successful"
    assert runner.cluster_for(cleanup_run) is None
    destroy_mock.assert_called_once()


def test_legacy_run_keeps_per_run_cleanup(benchmark, cluster, mocker):
    run = benchmarks.enqueue(benchmark)
    run.reuse_cluster = False
    run.phase, run.outcome = "cleanup", "successful"
    cluster.benchmark_run_id = run.id
    cluster.status = Status.NOT_DEPLOYED
    cluster.tfcloud_run.plan = {"resource_changes": []}
    db.session.commit()
    mocker.patch.object(MagicCastle, "_update_status_from_tf_cloud")
    destroy = mocker.patch.object(MagicCastle, "destroy_empty_cluster")
    runner.advance_run(run.id)
    destroy.assert_called_once()
    assert run.phase == "complete"


def test_unverified_workspace_blocks_cleanup_and_next_run(benchmark, cluster, mocker):
    run = benchmarks.enqueue(benchmark)
    run.phase, run.outcome = "cleanup", "successful"
    cluster.benchmark_run_id = run.id
    cluster.status = Status.NOT_DEPLOYED
    cluster.tfcloud_run.plan = {"resource_changes": []}
    cluster.tfcloud_workspace = "workspace"
    db.session.commit()
    mocker.patch.object(MagicCastle, "_update_status_from_tf_cloud")
    tf = mocker.patch.object(runner, "get_terraform_cloud").return_value
    tf.verify_workspace_empty.side_effect = InvalidUsageException("Resources remain")
    with pytest.raises(InvalidUsageException, match="Resources remain"):
        runner.advance_run(run.id)
    assert run.phase == "cleanup"
    assert run.active_benchmark_id == benchmark.id
    with pytest.raises(InvalidUsageException):
        benchmarks.enqueue(benchmark)
    assert runner.cluster_for(run) is cluster


@pytest.mark.parametrize("workspace", [None, "ws-existing"])
def test_retry_incomplete_setup_reuses_recorded_integrations(benchmark, cluster, mocker, workspace):
    import mchub.models.magic_castle.magic_castle as mc_module
    previous = benchmarks.enqueue(benchmark)
    previous.phase, previous.active_benchmark_id = "complete", None
    previous.outcome = "failed"
    cluster.benchmark_run_id = previous.id
    cluster.hostname = previous.hostname
    cluster.config = MagicCastleConfiguration("openstack", previous.configuration)
    cluster.status, cluster.undeployed = Status.NOT_DEPLOYED, True
    cluster.tfcloud_run = TerraformCloudRunORM()
    cluster.tfcloud_workspace = workspace
    cluster.usage_repository = "org/retained-repo"
    cluster.eyaml_public_key = None
    db.session.commit()
    current = benchmarks.enqueue(benchmark)
    db.session.commit()
    tf = mocker.patch.object(runner, "get_terraform_cloud").return_value
    mocker.patch.object(mc_module, "get_terraform_cloud", return_value=tf)
    tf.create_workspace.return_value = "ws-created"
    storage = mocker.patch.object(mc_module, "get_github_storage").return_value
    storage.write.return_value = "new-sha"
    mocker.patch.object(mc_module.DnsManager, "get_environment_variables", return_value={})
    mocker.patch.object(MagicCastle, "_update_status_from_tf_cloud")
    def plan(self, github_sha, timeout):
        self.orm.tfcloud_run = TerraformCloudRunORM(run_id="new-run", commit_sha=github_sha)
        self.orm.status = Status.CREATED
        db.session.commit()
    mocker.patch.object(MagicCastle, "create_plan", plan)
    runner.advance_run(current.id)
    assert current.phase == "ready"
    assert cluster.benchmark_run_id == current.id
    assert cluster.usage_repository == "org/retained-repo"
    assert cluster.tfcloud_workspace == (workspace or "ws-created")
    assert cluster.eyaml_public_key is not None
    storage.create_repo.assert_not_called()
    if workspace:
        tf.create_workspace.assert_not_called()
    else:
        tf.create_workspace.assert_called_once()
    tf.upsert_workspace_variable_set.assert_called_once()


def test_scheduler_coalesces_missed_runs_and_never_overlaps(benchmark):
    with freeze_time("2027-01-01"):
        benchmark.next_run_at = utcnow() - timedelta(days=10)
        db.session.commit()
        benchmarks.schedule_due()
        benchmarks.schedule_due()
        assert len(db.session.scalars(db.select(BenchmarkRun)).all()) == 1
        assert benchmark.next_run_at == utcnow() + timedelta(hours=1)
    with freeze_time("2027-01-03"):
        benchmarks.schedule_due()
        assert len(db.session.scalars(db.select(BenchmarkRun)).all()) == 1
        assert benchmark.next_run_at == utcnow() + timedelta(hours=1)


@pytest.mark.parametrize("criterion", ["healthy", "build_completed"])
def test_successful_run_measures_then_cleans_up_and_is_excluded_from_adoption(app, benchmark, mocker, criterion, setup_backends):
    benchmark.success_criterion = criterion
    mocker.patch.object(runner, "ensure_aws_feasible")
    mocker.patch.object(MagicCastle, "_update_status_from_tf_cloud")
    mocker.patch.object(MagicCastle, "services_are_online", new_callable=PropertyMock, return_value=True)
    storage, tf = setup_backends
    tf.create_workspace.side_effect = None
    tf.create_workspace.return_value = "ws-test"
    mocker.patch.object(runner, "get_terraform_cloud", return_value=tf)
    create = mocker.spy(MagicCastle, "plan_creation")
    initial_plan = mocker.patch.object(MagicCastle, "create_plan")
    benchmark.setup_status = "pending"
    db.session.commit()
    saved = app.test_client().put(f"/api/benchmarks/{benchmark.id}", json=payload(benchmark), headers=OWNER_HEADERS)
    assert saved.status_code == 200
    assert saved.get_json()["setup_status"] == "ready"
    initial_plan.assert_not_called()
    assert db.session.scalar(db.select(BenchmarkRun)) is None
    storage.write.assert_called_once()
    assert storage.write.call_args.kwargs == {"trigger_run": False}
    def initial_deployment(self, github_sha, timeout, run_id=None):
        assert run_id is None
        self.orm.tfcloud_run = TerraformCloudRunORM(run_id="run-benchmark", commit_sha=github_sha, plan={"resource_changes": []})
        self.orm.status = Status.CREATED
        db.session.commit()
    mocker.patch.object(MagicCastle, "create_plan", initial_deployment)
    tf.get_run_status.side_effect = [(TFStatus.PLANNED, False), (TFStatus.APPLIED, False)]
    def apply(self, initiated_by=None):
        usage.accepted(usage.begin_apply(self.orm, initiated_by))
        self.orm.undeployed = False
        self.orm.status = Status.PROVISIONING_RUNNING
        db.session.commit()
    mocker.patch.object(MagicCastle, "apply", apply)
    with freeze_time("2027-01-01 00:00:00"):
        run = benchmarks.enqueue(benchmark)
        db.session.commit()
        runner.advance_run(run.id)
        assert run.phase == "ready"
        runner.advance_run(run.id)
        assert run.phase == "waiting"
    with freeze_time("2027-01-01 00:05:00"):
        runner.advance_run(run.id)
        assert run.outcome == "successful"
        if criterion == "healthy":
            assert run.target_reached_at == run.healthy_at
        else:
            assert run.healthy_at is None
        assert run.duration_seconds == 300
        assert run.active_benchmark_id == benchmark.id
        with app.test_request_context("/api/usage?start=2027-01-01&end=2027-01-31"):
            assert UsageAPI().get(SimpleNamespace(is_admin=True))["summary"]["successful_deployments"] == 0
    tf.get_run_status.side_effect = None
    tf.get_run_status.return_value = (None, False)
    mocker.patch.object(cluster_lifecycle, "plan_teardown", side_effect=lambda *_: MagicCastle(runner.cluster_for(run)).complete_teardown())
    def destroy(self):
        db.session.delete(self.orm)
        db.session.commit()
    mocker.patch.object(MagicCastle, "destroy_empty_cluster", destroy)
    runner.advance_run(run.id)
    assert run.phase == "cleanup"
    runner.advance_run(run.id)
    assert run.phase == "complete"
    assert run.active_benchmark_id is None
    assert run.cleanup_at is not None
    assert run.terraform_run_id == "run-benchmark"
    assert run.commit_sha == "initial-sha"
    assert run.duration_seconds == 300
    retained = runner.cluster_for(run)
    assert retained is not None
    assert retained.undeployed
    assert retained.tfcloud_workspace == "ws-test"
    tf.verify_workspace_empty.assert_called_with("ws-test")
    # A second deployment uses the same commit and a distinct Terraform run.
    tf.plan_from_commit.return_value = "run-next"
    def plan(self, github_sha, timeout, run_id=None):
        assert 0 < timeout <= runner.STEP_TIMEOUT - 10
        assert run_id == "run-next"
        self.orm.tfcloud_run = TerraformCloudRunORM(run_id=run_id, commit_sha=github_sha, plan={"resource_changes": []})
        self.orm.status = Status.CREATED
        db.session.commit()
    mocker.patch.object(MagicCastle, "create_plan", plan)
    if criterion == "build_completed":
        tf.get_run_status.side_effect = [(TFStatus.PLANNED, False), (TFStatus.APPLIED, False)]
    with freeze_time("2027-01-01 00:10:00"):
        next_run = benchmarks.enqueue(benchmark)
        db.session.commit()
        runner.advance_run(next_run.id)
        assert runner.cluster_for(next_run).id == retained.id
        assert next_run.terraform_run_id == "run-next"
        assert next_run.applied_at is None
        assert next_run.healthy_at is None
        runner.advance_run(next_run.id)
    with freeze_time("2027-01-01 00:13:00"):
        runner.advance_run(next_run.id)
    assert next_run.outcome == "successful"
    assert next_run.duration_seconds == 180
    assert next_run.hostname == run.hostname
    assert next_run.repository == run.repository
    assert next_run.commit_sha == run.commit_sha
    assert run.terraform_run_id == "run-benchmark"
    assert run.duration_seconds == 300
    create.assert_called_once()
    storage.create_repo.assert_called_once()
    tf.create_workspace.assert_called_once()
    storage.write.assert_called_once()  # Both runs deploy the first save's commit.
    storage.trigger_run.assert_called_once_with(run.hostname, "initial-sha")
    assert tf.plan_from_commit.call_count == 2
    assert tf.upsert_workspace_variable_set.call_args.args[0] == "ws-test"
    assert tf.upsert_workspace_variable_set.call_args.args[1][0].value == "[]"


@pytest.mark.parametrize("remote,is_destroy,expected", [
    (TFStatus.APPLIED, False, "successful"),
    (TFStatus.PLANNED_AND_FINISHED, False, "successful"),
    (TFStatus.APPLYING, False, None),
    (TFStatus.PLANNED, False, None),
    (TFStatus.APPLIED, True, None),
    (TFStatus.APPLIED, None, None),
    (TFStatus.ERRORED, False, "failed"),
])
def test_build_target_uses_completed_deployment_without_health_checks(benchmark, cluster, mocker, remote, is_destroy, expected):
    benchmark.success_criterion = "build_completed"
    with freeze_time("2027-01-01 00:00:00"):
        run = benchmarks.enqueue(benchmark)
        cluster.benchmark_run_id = run.id
        run.phase, run.started_at = "waiting", utcnow()
        usage.accepted(usage.begin_apply(cluster))
        db.session.commit()
    tf = mocker.patch.object(runner, "get_terraform_cloud").return_value
    tf.get_run_status.return_value = (remote, is_destroy)
    # Even a failed or stalled health probe must not block this criterion.
    health = mocker.patch.object(MagicCastle, "status", new_callable=PropertyMock, side_effect=AssertionError("Probed health"))
    with freeze_time("2027-01-01 00:05:00"):
        runner.advance_run(run.id)
        assert run.outcome == expected
        assert run.healthy_at is None
        health.assert_not_called()
        tf.get_run_status.assert_called_once_with("run-1")
        if expected == "successful":
            assert run.phase == "cleanup"
            assert run.target_reached_at == utcnow()
            assert run.duration_seconds == 300
            # Later edits and cleanup cannot replace this run's result.
            benchmark.success_criterion = "healthy"
            runner.refresh_measurement(run, cluster)
            assert run.success_criterion == "build_completed"
            assert run.duration_seconds == 300
        else:
            assert run.target_reached_at is None


def test_healthy_target_waits_after_build_completion(benchmark, cluster, mocker):
    run = benchmarks.enqueue(benchmark)
    cluster.benchmark_run_id = run.id
    run.phase, run.started_at = "waiting", utcnow()
    cluster.status = Status.PROVISIONING_RUNNING
    usage.accepted(usage.begin_apply(cluster))
    db.session.commit()
    mocker.patch.object(MagicCastle, "_update_status_from_tf_cloud")
    mocker.patch.object(MagicCastle, "services_are_online", new_callable=PropertyMock, return_value=False)
    runner.advance_run(run.id)
    assert run.phase == "waiting"
    assert run.outcome is None
    assert run.target_reached_at is None


def test_build_target_observed_after_deadline_times_out(benchmark, cluster, mocker):
    benchmark.success_criterion = "build_completed"
    run = benchmarks.enqueue(benchmark)
    cluster.benchmark_run_id = run.id
    run.phase, run.started_at = "waiting", utcnow() - timedelta(hours=3)
    db.session.commit()
    mocker.patch.object(runner, "get_terraform_cloud").return_value.get_run_status.return_value = (TFStatus.APPLIED, False)
    runner.advance_run(run.id)
    assert run.outcome == "timed_out"
    assert run.phase == "cleanup"


def test_statistics_compare_only_runs_with_current_success_criterion(app, benchmark):
    for criterion, outcome, seconds in [("healthy", "successful", 600), ("build_completed", "successful", 120),
                                        ("healthy", "failed", None)]:
        benchmark.success_criterion = criterion
        run = benchmarks.enqueue(benchmark)
        run.phase, run.active_benchmark_id = "complete", None
        run.applied_at = utcnow()
        run.outcome = outcome
        run.commit_sha, run.repository = "same-sha", "org/repo"
        run.target_reached_at = run.applied_at + timedelta(seconds=seconds) if seconds else None
        db.session.commit()
    client = app.test_client()
    url = f"/api/benchmarks/{benchmark.id}"
    healthy_report = client.get(url, headers=OWNER_HEADERS).get_json()
    assert healthy_report["timing"]["average_seconds"] == 600
    assert healthy_report["success_rate"] == 0.5
    benchmark.success_criterion = "build_completed"
    db.session.commit()
    build_report = client.get(url, headers=OWNER_HEADERS).get_json()
    assert build_report["timing"]["average_seconds"] == 120
    assert build_report["success_rate"] == 1
    assert build_report["total_runs"] == 3
    assert {r["success_criterion"] for r in build_report["runs"]} == {"healthy", "build_completed"}
    assert all(r["target_reached_at"] for r in build_report["runs"] if r["outcome"] == "successful")


def test_proxy_token_and_encrypted_puppet_values_reuse_commit_until_specifications_change(app, benchmark, setup_backends, mocker):
    from mchub.configuration import get_config
    get_config()["mchub_url"] = "https://hub.example.org"
    storage, tf = setup_backends
    mocker.patch.object(runner, "get_terraform_cloud", return_value=tf)
    mocker.patch.object(runner, "ensure_aws_feasible")
    mocker.patch.object(MagicCastle, "_update_status_from_tf_cloud")
    encrypt = mocker.spy(mc_module, "_encrypt_eyaml")
    benchmark.configuration = {**benchmark.configuration, "hieradata_entries": [
        {"key": "profile::secret", "value": "secret-puppet-value", "encrypt": True},
    ]}
    benchmark.setup_status = "pending"
    db.session.commit()
    client = app.test_client()
    url = f"/api/benchmarks/{benchmark.id}"
    assert client.put(url, json=payload(benchmark), headers=OWNER_HEADERS).status_code == 200
    orm = benchmarks.reusable_cluster(benchmark.id)
    original_token = orm.cluster_token
    assert original_token
    original_hieradata = storage.write.call_args.args[0]["hieradata"]
    assert "profile::slurm::controller::tfe_token: ENC[PKCS7," in original_hieradata
    assert "profile::secret: ENC[PKCS7," in original_hieradata
    assert original_token not in original_hieradata
    assert "secret-puppet-value" not in original_hieradata
    encryption_count = encrypt.call_count

    tf.plan_from_commit.side_effect = ["run-first", "run-metadata", None]
    def plan(self, github_sha, run_id=None, timeout=None):
        self.orm.tfcloud_run = TerraformCloudRunORM(run_id=run_id or "run-new-specs", commit_sha=github_sha)
        self.orm.status = Status.CREATED
        db.session.commit()
    mocker.patch.object(MagicCastle, "create_plan", plan)
    def prepare_and_finish():
        run = benchmarks.enqueue(benchmark)
        db.session.commit()
        runner.advance_run(run.id)
        assert run.phase == "ready"
        # This regression exercises planning only; no cloud resources are applied.
        MagicCastle(orm).complete_teardown()
        run.phase, run.active_benchmark_id = "complete", None
        db.session.commit()
        return run

    first = prepare_and_finish()
    metadata = deepcopy(payload(benchmark))
    metadata.update(name="Renamed benchmark", frequency="weekly", enabled=False)
    metadata["configuration"]["availability_zone"] = None  # Added by the shared editor.
    assert client.put(url, json=metadata, headers=OWNER_HEADERS).status_code == 200
    second = prepare_and_finish()
    assert first.commit_sha == second.commit_sha == "initial-sha"
    assert first.terraform_run_id != second.terraform_run_id
    assert first.revision != second.revision
    assert orm.cluster_token == original_token
    assert encrypt.call_count == encryption_count
    storage.write.assert_called_once()
    storage.trigger_run.assert_not_called()

    changed = deepcopy(payload(benchmark))
    changed["configuration"]["instances"]["node"]["count"] += 1
    assert client.put(url, json=changed, headers=OWNER_HEADERS).status_code == 200
    storage.write.return_value = "changed-specification-sha"
    third = prepare_and_finish()
    assert third.commit_sha == "changed-specification-sha"
    assert first.commit_sha == second.commit_sha == "initial-sha"
    assert storage.write.call_count == 2
    assert encrypt.call_count > encryption_count
    assert orm.cluster_token == original_token
    assert storage.write.call_args.kwargs == {"trigger_run": False}
    storage.trigger_run.assert_called_once_with(orm.hostname, third.commit_sha)


def test_comparison_groups_use_full_commit_and_criterion_preserving_unknown_runs(app, benchmark):
    records = [("old-sha", "healthy", "successful", 600),
               ("new-sha", "healthy", "successful", 120),
               ("new-sha", "healthy", "failed", None),
               ("new-sha", "build_completed", "successful", 60),
               (None, "healthy", "successful", 999)]
    for index, (sha, criterion, outcome, seconds) in enumerate(records):
        benchmark.success_criterion = criterion
        run = benchmarks.enqueue(benchmark)
        run.phase, run.active_benchmark_id = "complete", None
        run.requested_at = utcnow() + timedelta(seconds=index)
        run.applied_at = utcnow()
        run.outcome, run.commit_sha, run.repository = outcome, sha, "org/repo"
        run.target_reached_at = run.applied_at + timedelta(seconds=seconds) if seconds else None
        # Identical specifications with different SHAs must still stay separate.
        db.session.commit()
    report = app.test_client().get(f"/api/benchmarks/{benchmark.id}", headers=OWNER_HEADERS).get_json()
    groups = {(g["commit_sha"], g["success_criterion"]): g for g in report["comparison_groups"]}
    assert len(groups) == 3
    assert groups[("old-sha", "healthy")]["timing"]["average_seconds"] == 600
    assert groups[("new-sha", "healthy")]["timing"]["average_seconds"] == 120
    assert groups[("new-sha", "healthy")]["success_rate"] == 0.5
    assert groups[("new-sha", "build_completed")]["timing"]["average_seconds"] == 60
    assert report["default_comparison_group"] == groups[("new-sha", "healthy")]["id"]
    assert report["timing"]["average_seconds"] == 120
    assert report["success_rate"] == 0.5
    assert report["unassigned_runs"] == 1
    assert report["total_runs"] == len(report["runs"]) == 5


@pytest.mark.parametrize("remote_error", [False, True])
def test_existing_import_tag_waits_for_a_fresh_run_and_preserves_failure_commit(app, benchmark, setup_backends, mocker, remote_error):
    storage, tf = setup_backends
    benchmark.setup_status = "pending"
    db.session.commit()
    assert app.test_client().put(f"/api/benchmarks/{benchmark.id}", json=payload(benchmark), headers=OWNER_HEADERS).status_code == 200
    orm = benchmarks.reusable_cluster(benchmark.id)
    run = benchmarks.enqueue(benchmark)
    orm.benchmark_run_id = run.id
    db.session.commit()
    storage.trigger_run.return_value = False
    tf.plan_from_commit.side_effect = [None, RuntimeError("API failed") if remote_error else "fresh-run"]
    plan = mocker.patch.object(MagicCastle, "create_plan")
    if remote_error:
        with pytest.raises(RuntimeError, match="API failed"):
            MagicCastle(orm).plan_benchmark_run(run.configuration, timeout=30)
        runner.refresh_measurement(run, orm)
        assert run.commit_sha == "initial-sha"
        assert run.terraform_run_id is None
        plan.assert_not_called()
    else:
        MagicCastle(orm).plan_benchmark_run(run.configuration, timeout=30)
        assert plan.call_args.kwargs["run_id"] == "fresh-run"
        assert plan.call_args.kwargs["github_sha"] == "initial-sha"
    storage.write.assert_called_once()


def test_group_summaries_cover_history_beyond_the_display_limit(app, benchmark):
    now = utcnow()
    runs = [BenchmarkRun(
        benchmark_id=benchmark.id, configuration=deepcopy(benchmark.configuration), revision=1,
        timeout_minutes=120, hostname="benchmark.example.org", repository="org/repo",
        commit_sha="shared-sha", success_criterion="healthy", requested_at=now - timedelta(seconds=index),
        applied_at=now, target_reached_at=now + timedelta(seconds=120), phase="complete", outcome="successful",
    ) for index in range(501)]
    db.session.add_all(runs)
    db.session.commit()
    report = app.test_client().get(f"/api/benchmarks/{benchmark.id}", headers=OWNER_HEADERS).get_json()
    assert len(report["runs"]) == 500
    assert report["comparison_groups"][0]["total_runs"] == 501
    assert report["comparison_groups"][0]["timing"] == {
        "count": 501, "average_seconds": 120, "median_seconds": 120, "p95_seconds": 120,
    }


def test_timeout_busy_cleanup_and_retry_keeps_benchmark_locked(benchmark, cluster, mocker):
    run = benchmarks.enqueue(benchmark)
    db.session.commit()
    run.phase = "waiting"
    run.started_at = utcnow() - timedelta(hours=3)
    cluster.benchmark_run_id = run.id
    cluster.status = Status.BUILD_RUNNING
    cluster.undeployed = False
    db.session.commit()
    mocker.patch.object(MagicCastle, "_update_status_from_tf_cloud")
    runner.advance_run(run.id)
    assert run.outcome == "timed_out"
    cluster.tfcloud_run.plan = {"resource_changes": []}
    db.session.commit()
    runner.advance_run(run.id)
    assert run.phase == "cleanup"
    assert "Waiting" in run.cleanup_error
    runner.record_error(run.id, "Cleanup failed")
    assert run.outcome == "timed_out"
    assert run.cleanup_error == "Cleanup failed"
    with pytest.raises(InvalidUsageException):
        benchmarks.enqueue(benchmark)


def test_interrupted_apply_is_not_replayed_and_cluster_edits_are_blocked(benchmark, cluster, mocker):
    run = benchmarks.enqueue(benchmark)
    db.session.commit()
    run.phase, run.started_at = "applying", utcnow()
    cluster.benchmark_run_id = run.id
    cluster.status = Status.CREATED
    db.session.commit()
    mocker.patch.object(MagicCastle, "_update_status_from_tf_cloud")
    apply = mocker.patch.object(MagicCastle, "apply")
    runner.advance_run(run.id)
    assert run.phase == "waiting"
    apply.assert_not_called()
    with pytest.raises(InvalidUsageException, match="managed by its benchmark"):
        cluster_lifecycle.claim_background_task(cluster)


def test_migration_preserves_existing_usage():
    migration = importlib.import_module("migrations.versions.0012_benchmarks")
    with create_engine("sqlite://").begin() as connection:
        for table in ("magiccastle", "usage_lifetime"):
            connection.execute(text(f"CREATE TABLE {table} (id INTEGER PRIMARY KEY)"))
            connection.execute(text(f"INSERT INTO {table} VALUES (1)"))
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
            assert connection.execute(text("SELECT benchmark_run_id FROM usage_lifetime")).scalar() is None
            migration.downgrade()
        assert set(inspect(connection).get_table_names()) == {"magiccastle", "usage_lifetime"}


def test_criterion_migration_preserves_historical_healthy_results():
    migration = importlib.import_module("migrations.versions.0013_benchmark_success_criterion")
    with create_engine("sqlite://").begin() as connection:
        connection.execute(text("CREATE TABLE benchmark (id INTEGER PRIMARY KEY)"))
        connection.execute(text("CREATE TABLE benchmark_run (id INTEGER PRIMARY KEY, healthy_at DATETIME)"))
        connection.execute(text("INSERT INTO benchmark VALUES (1)"))
        connection.execute(text("INSERT INTO benchmark_run VALUES (1, '2027-01-01 00:05:00'), (2, NULL)"))
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
            assert connection.execute(text("SELECT success_criterion FROM benchmark")).scalar() == "healthy"
            assert connection.execute(text("SELECT success_criterion, target_reached_at FROM benchmark_run ORDER BY id")).all() == [
                ("healthy", "2027-01-01 00:05:00"), ("healthy", None)]
            migration.downgrade()
        assert connection.execute(text("SELECT healthy_at FROM benchmark_run ORDER BY id")).all() == [
            ("2027-01-01 00:05:00",), (None,)]
        assert [c["name"] for c in inspect(connection).get_columns("benchmark")] == ["id"]


def test_reuse_migration_preserves_legacy_runs_and_allows_repeated_hostnames():
    migration = importlib.import_module("migrations.versions.0014_reusable_benchmark_clusters")
    with create_engine("sqlite://").begin() as connection:
        connection.execute(text("CREATE TABLE benchmark (id TEXT PRIMARY KEY)"))
        connection.execute(text("CREATE TABLE benchmark_run (id TEXT PRIMARY KEY, hostname TEXT NOT NULL UNIQUE, active_benchmark_id TEXT UNIQUE)"))
        connection.execute(text("INSERT INTO benchmark VALUES ('benchmark')"))
        connection.execute(text("INSERT INTO benchmark_run VALUES ('old', 'cluster.example.org', NULL)"))
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
            assert connection.execute(text("SELECT cluster_name FROM benchmark")).scalar() is None
            assert connection.execute(text("SELECT reuse_cluster FROM benchmark_run")).scalar() == 0
            connection.execute(text("INSERT INTO benchmark_run VALUES ('new', 'cluster.example.org', 'benchmark', 1)"))
            assert connection.execute(text("SELECT COUNT(*) FROM benchmark_run")).scalar() == 2
            assert {tuple(c["column_names"]) for c in inspect(connection).get_unique_constraints("benchmark_run")} == {("active_benchmark_id",)}
            with pytest.raises(RuntimeError, match="share hostnames"):
                migration.downgrade()
            connection.execute(text("DELETE FROM benchmark_run WHERE id = 'new'"))
            migration.downgrade()
        assert connection.execute(text("SELECT hostname FROM benchmark_run")).scalar() == "cluster.example.org"


def test_setup_migration_adopts_reusable_integrations_and_preserves_legacy_ownership():
    migration = importlib.import_module("migrations.versions.0015_benchmark_setup")
    with create_engine("sqlite://").begin() as connection:
        connection.execute(text("CREATE TABLE benchmark (id TEXT PRIMARY KEY)"))
        connection.execute(text("CREATE TABLE benchmark_run (id TEXT PRIMARY KEY, benchmark_id TEXT, reuse_cluster BOOLEAN)"))
        connection.execute(text("""CREATE TABLE magiccastle (id INTEGER PRIMARY KEY, benchmark_run_id TEXT,
            usage_repository TEXT, tfcloud_workspace TEXT, eyaml_public_key TEXT)"""))
        connection.execute(text("INSERT INTO benchmark VALUES ('reusable'), ('legacy'), ('new')"))
        connection.execute(text("INSERT INTO benchmark_run VALUES ('run-1', 'reusable', 1), ('run-2', 'legacy', 0)"))
        connection.execute(text("""INSERT INTO magiccastle VALUES
            (1, 'run-1', 'org/repo', 'ws-reuse', 'key'), (2, 'run-2', 'org/legacy', 'ws-old', 'key')"""))
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
            assert connection.execute(text("SELECT id, setup_status FROM benchmark ORDER BY id")).all() == [
                ("legacy", "pending"), ("new", "pending"), ("reusable", "ready")]
            assert connection.execute(text("SELECT id, benchmark_id FROM magiccastle ORDER BY id")).all() == [(1, "reusable"), (2, None)]
            connection.execute(text("INSERT INTO magiccastle (id, benchmark_id) VALUES (3, 'new')"))
            with pytest.raises(RuntimeError, match="have not run"):
                migration.downgrade()
            connection.execute(text("DELETE FROM magiccastle WHERE id = 3"))
            migration.downgrade()
        assert connection.execute(text("SELECT benchmark_run_id FROM magiccastle ORDER BY id")).all() == [("run-1",), ("run-2",)]
        assert [column["name"] for column in inspect(connection).get_columns("benchmark")] == ["id"]


def test_commit_migration_preserves_historical_run_shas():
    migration = importlib.import_module("migrations.versions.0016_benchmark_commits")
    with create_engine("sqlite://").begin() as connection:
        connection.execute(text("CREATE TABLE magiccastle (id INTEGER PRIMARY KEY)"))
        connection.execute(text("INSERT INTO magiccastle VALUES (1)"))
        connection.execute(text("CREATE TABLE benchmark_run (id INTEGER PRIMARY KEY, commit_sha TEXT)"))
        connection.execute(text("INSERT INTO benchmark_run VALUES (1, 'original-sha')"))
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
            assert connection.execute(text("SELECT benchmark_configuration, benchmark_commit_sha FROM magiccastle")).one() == (None, None)
            assert connection.execute(text("SELECT commit_sha FROM benchmark_run")).scalar() == "original-sha"
            migration.downgrade()
        assert [column["name"] for column in inspect(connection).get_columns("magiccastle")] == ["id"]
        assert connection.execute(text("SELECT commit_sha FROM benchmark_run")).scalar() == "original-sha"


def test_pause_does_not_require_version_to_remain_in_catalog(app, benchmark, mocker):
    mocker.patch.object(MagicCastle, "validate_creation_version", side_effect=InvalidUsageException("Old version"))
    response = app.test_client().patch(f"/api/benchmarks/{benchmark.id}", json={"enabled": False}, headers=OWNER_HEADERS)
    assert response.status_code == 200
    assert benchmark.enabled is False
    benchmarks.schedule_due()
    assert not db.session.scalar(db.select(BenchmarkRun))


def test_interrupted_creation_moves_to_cleanup_instead_of_staying_busy(benchmark, cluster, mocker):
    run = benchmarks.enqueue(benchmark)
    db.session.commit()
    run.phase, run.started_at = "creating", utcnow()
    cluster.benchmark_run_id = run.id
    cluster.status = Status.PLAN_RUNNING
    db.session.commit()
    runner.advance_run(run.id)
    assert run.phase == "cleanup"
    assert run.outcome == "failed"
    assert cluster.status == Status.PLAN_ERROR


def test_scheduler_launches_isolated_steps_and_stops_them_on_shutdown(app, benchmark, mocker):
    from threading import Event
    import os
    run = benchmarks.enqueue(benchmark)
    db.session.commit()
    run_id = run.id
    stop = Event()
    mocker.patch.object(stop, "wait", side_effect=lambda _: stop.set())
    mocker.patch.object(runner, "Event", return_value=stop)
    mocker.patch.object(runner, "create_app", return_value=app)
    mocker.patch.object(runner.signal, "signal")
    process = mocker.Mock()
    process.poll.return_value = None
    popen = mocker.patch.object(runner.subprocess, "Popen", return_value=process)
    runner.main()
    assert popen.call_args.args[0][1:] == ["-m", "mchub.services.benchmark_runner", "--step", run_id, "--parent", str(os.getpid())]
    process.terminate.assert_called_once()
    process.wait.assert_called_once_with(timeout=5)


def test_membership_and_hub_admin_status_do_not_grant_benchmark_access(app, benchmark, cluster):
    cluster.project.admins.remove(cluster.created_by)
    db.session.commit()
    client = app.test_client()
    assert client.get("/api/benchmarks", headers=OWNER_HEADERS).status_code == 403
    hub_admin = {**ALICE_HEADERS, "eduPersonPrincipalName": "the-admin@computecanada.ca"}
    assert client.get("/api/benchmarks", headers=hub_admin).status_code == 403
