import json
import importlib

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect

from mchub import create_app
from mchub.database import db
from mchub.services import service_status as status
from mchub.models.service_status import ServiceStatusSnapshot
from tests.mocks.configuration.config_mock import config_auth_saml_mock as config_mock
from tests.data import ALICE_HEADERS


@pytest.fixture
def app(config_mock):
    app = create_app("sqlite://")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def rss(state="Investigating", component="HCP Terraform", identity="one"):
    components = f"<b>Affected components</b><ul><li>{component} (Under maintenance)</li></ul>" if component else ""
    return f'''<rss><channel><item><guid>{identity}</guid><title>Delayed runs</title>
    <link>https://status.hashicorp.com/incidents/one</link>
    <description><![CDATA[<b>Status: {state}</b><br/>Some explanation.
    {components}]]></description>
    </item></channel></rss>'''.encode()


@pytest.mark.parametrize("state", ["Resolved", "Complete", "Completed", "Scheduled"])
def test_rss_inactive_without_components_is_silent(state, caplog):
    result = status.hashicorp_rss(rss(state, component=None), status.DEFAULT_PROVIDERS[1])
    assert result["seen_ids"] == ["one"]
    assert result["reported_status"] == "no_incidents"
    assert not caplog.records


def test_rss_unclassified_warnings_only_for_new_or_changed_entries(mocker, caplog):
    mocker.patch.object(status, "_rss_unclassified", {})
    provider = status.DEFAULT_PROVIDERS[1]
    status.hashicorp_rss(rss(component=None), provider)
    status.hashicorp_rss(rss(component=None), provider)
    assert len(caplog.records) == 1
    status.hashicorp_rss(rss("Monitoring", component=None), provider)
    assert len(caplog.records) == 2
    status.hashicorp_rss(rss("Monitoring", component=None, identity="two"), provider)
    assert len(caplog.records) == 3
    status.hashicorp_rss(rss("Resolved", component=None, identity="two"), provider)
    assert len(caplog.records) == 3
    assert status._rss_unclassified[(provider["id"], provider["feed_url"])] == {}


def test_rss_resolution_without_components_clears_tracked_incident(app, mocker):
    provider = status.DEFAULT_PROVIDERS[1]
    mocker.patch.object(status, "providers", return_value=[provider])
    fetch = mocker.patch.object(status, "fetch", side_effect=lambda p: status.hashicorp_rss(rss(), p))
    status.poll_once()
    assert status.read_status()["providers"][0]["reported_status"] == "disruption"
    # Missing classification on an active update must not falsely clear it.
    fetch.side_effect = lambda p: status.hashicorp_rss(rss(component=None), p)
    status.poll_once()
    assert status.read_status()["providers"][0]["incidents"][0]["confirmed"] is False
    fetch.side_effect = lambda p: status.hashicorp_rss(rss("Resolved", component=None), p)
    status.poll_once()
    result = status.read_status()["providers"][0]
    assert result["reported_status"] == "no_incidents"
    assert result["incidents"] == []


def test_rss_filters_and_resolves():
    provider = status.DEFAULT_PROVIDERS[1]
    assert status.hashicorp_rss(rss(), provider)["incidents"][0]["status"] == "investigating"
    for state in ("Resolved", "Complete", "Scheduled"):
        result = status.hashicorp_rss(rss(state), provider)
        assert result["incidents"] == []
        assert result["seen_ids"] == ["one"]
    assert status.hashicorp_rss(rss(component="HCP Vault Radar"), provider)["incidents"] == []
    with pytest.raises(ValueError):
        status.hashicorp_rss(rss("Unexpected"), provider)
    with pytest.raises(ValueError):
        status.hashicorp_rss(b"<html/>", provider)


def test_statuspage_filters_and_validates():
    provider = {**status.DEFAULT_PROVIDERS[0], "components": ["Git Operations"]}
    data = dict(components=[dict(id="git", name="Git Operations", status="operational")],
        incidents=[dict(id="x", name="Copilot", status="investigating", components=[dict(id="copilot")])])
    assert status.statuspage(json.dumps(data), provider)["reported_status"] == "no_incidents"
    data["incidents"][0]["components"] = [dict(id="git")]
    data["incidents"][0]["status"] = "monitoring"
    data["incidents"][0]["shortlink"] = "javascript:alert(1)"
    result = status.statuspage(json.dumps(data), provider)
    assert result["reported_status"] == "disruption"
    assert result["incidents"][0]["url"] == provider["status_url"]
    data["components"] = []
    with pytest.raises(ValueError):
        status.statuspage(json.dumps(data), provider)


def test_poll_failure_staleness_and_recovery(app, mocker):
    clock = mocker.patch.object(status, "now", return_value=1000)
    provider = status.DEFAULT_PROVIDERS[1]
    mocker.patch.object(status, "providers", return_value=[provider])
    fetch = mocker.patch.object(status, "fetch", side_effect=lambda p: status.hashicorp_rss(rss(), p))
    status.poll_once()
    assert status.read_status()["providers"][0]["freshness"] == "fresh"
    fetch.side_effect = TimeoutError
    clock.return_value = 1180
    status.poll_once()
    result = status.read_status()["providers"][0]
    assert result["freshness"] == "stale"
    assert result["reported_status"] == "disruption"
    assert result["last_attempt_ok"] is False
    fetch.side_effect = lambda p: status.hashicorp_rss(b"<rss><channel/></rss>", p)
    status.poll_once()
    assert status.read_status()["providers"][0]["incidents"][0]["confirmed"] is False
    fetch.side_effect = lambda p: status.hashicorp_rss(rss("Resolved"), p)
    status.poll_once()
    assert status.read_status()["providers"][0]["reported_status"] == "no_incidents"


def test_provider_failure_isolated_and_endpoint_reads_only(app, mocker):
    def fetch(p):
        if p["id"] == "github":
            raise TimeoutError()
        return status.hashicorp_rss(rss(), p)
    network = mocker.patch.object(status, "fetch", side_effect=fetch)
    status.poll_once()
    assert db.session.get(ServiceStatusSnapshot, "terraform_cloud").last_attempt_ok
    network.reset_mock()
    response = app.test_client().get("/api/service-status", headers=ALICE_HEADERS)
    assert response.status_code == 200
    assert response.json["providers"][0]["freshness"] == "unknown"
    network.assert_not_called()
    assert app.test_client().get("/api/service-status").status_code == 400


def test_migration_roundtrip():
    migration = importlib.import_module("migrations.versions.0019_service_status")
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
            assert "service_status_snapshot" in inspect(connection).get_table_names()
            migration.downgrade()
            assert "service_status_snapshot" not in inspect(connection).get_table_names()


def test_provider_configuration_validation():
    from marshmallow import ValidationError
    from mchub.configuration import ConfigurationSchema
    config = dict(auth_type=["NONE"], cors_allowed_origins=[], magic_castle_version_range=">= 13.0.0")
    schema = ConfigurationSchema()
    assert schema.load({**config, "service_status_providers": []})["service_status_providers"] == []
    assert "service_status_providers" not in schema.load(config)
    assert len(schema.load({**config, "service_status_providers": status.DEFAULT_PROVIDERS})["service_status_providers"]) == 2
    with pytest.raises(ValidationError, match="unique"):
        schema.load({**config, "service_status_providers": [status.DEFAULT_PROVIDERS[0]] * 2})


def test_statuspage_unclassified_warnings_are_deduplicated(mocker, caplog):
    mocker.patch.object(status, "_statuspage_unclassified", {})
    provider = {**status.DEFAULT_PROVIDERS[0], "components": ["Git Operations"]}
    incident = dict(id="1dk955gg3bvz", name="Incident", status="investigating", components=[])
    data = dict(components=[dict(id="git", name="Git Operations", status="operational")], incidents=[incident])
    for _ in range(4):
        result = status.statuspage(json.dumps(data), provider)
    assert len(caplog.records) == 1
    assert result["reported_status"] == "no_incidents"
    # JSON key order is not an incident update.
    data["incidents"] = [dict(reversed(list(incident.items())))]
    status.statuspage(json.dumps(data), provider)
    assert len(caplog.records) == 1
    data["incidents"] = [incident]
    incident["status"] = "monitoring"
    status.statuspage(json.dumps(data), provider)
    status.statuspage(json.dumps(data), provider)
    assert len(caplog.records) == 2
    # Identical incident IDs from another provider must still be logged.
    status.statuspage(json.dumps(data), {**provider, "id": "other"})
    assert len(caplog.records) == 3
    incident["status"] = "resolved"
    status.statuspage(json.dumps(data), provider)
    assert len(caplog.records) == 3
    assert status._statuspage_unclassified[(provider["id"], provider["feed_url"])] == {}


def test_statuspage_invalid_feed_does_not_change_warning_cache(mocker, caplog):
    mocker.patch.object(status, "_statuspage_unclassified", {})
    provider = {**status.DEFAULT_PROVIDERS[0], "components": ["Git Operations"]}
    incident = dict(id="one", name="Incident", status="investigating", components=[])
    data = dict(components=[dict(id="git", name="Git Operations", status="operational")], incidents=[incident])
    status.statuspage(json.dumps(data), provider)
    data["incidents"].append(dict(id="two", status="unknown"))
    with pytest.raises(ValueError):
        status.statuspage(json.dumps(data), provider)
    data["incidents"].pop()
    status.statuspage(json.dumps(data), provider)
    assert len(caplog.records) == 1
    # A valid feed without the incident releases its fingerprint.
    data["incidents"] = []
    status.statuspage(json.dumps(data), provider)
    assert status._statuspage_unclassified[(provider["id"], provider["feed_url"])] == {}
