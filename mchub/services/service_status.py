"""Public status feed adapters and shared advisory snapshots."""
import json
import hashlib
import logging
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from ..configuration import get_config
from ..database import db
from ..models.service_status import ServiceStatusSnapshot

logger = logging.getLogger(__name__)
DEFAULT_PROVIDERS = [
    dict(id="github", name="GitHub", adapter="statuspage", enabled=True,
         feed_url="https://www.githubstatus.com/api/v2/summary.json",
         status_url="https://www.githubstatus.com/",
         components=["API Requests", "Git Operations", "Webhooks"]),
    dict(id="terraform_cloud", name="Terraform Cloud", adapter="hashicorp_rss", enabled=True,
         feed_url="https://status.hashicorp.com/feed.rss",
         status_url="https://status.hashicorp.com/", components=["HCP Terraform"]),
]
STALE_SECONDS = 180
# Only retain fingerprints from the latest valid feed. Warnings may recur after
# a worker restart, but unchanged incidents do not generate one per poll.
_rss_unclassified = {}


def providers():
    return [p for p in get_config().get("service_status_providers", DEFAULT_PROVIDERS) if p.get("enabled", True)]


def now():
    return datetime.now(timezone.utc).timestamp()


def iso(value):
    return datetime.fromtimestamp(value, timezone.utc).isoformat() if value is not None else None


def safe_url(value, fallback):
    return value if isinstance(value, str) and urlparse(value).scheme == "https" and urlparse(value).netloc else fallback


def statuspage(payload, provider):
    data = json.loads(payload)
    components = data["components"]
    watched = set(provider["components"])
    selected = [c for c in components if c["id"] in watched or c["name"] in watched]
    if any(not any(key in (c["id"], c["name"]) for c in selected) for key in watched):
        raise ValueError("Configured status component missing")
    valid = {"operational", "degraded_performance", "partial_outage", "major_outage", "under_maintenance"}
    if any(c["status"] not in valid for c in selected):
        raise ValueError("Unknown component status")
    ids = {c["id"] for c in selected}
    incidents = []
    for item in data["incidents"] + data.get("scheduled_maintenances", []):
        status = item["status"]
        if status in {"resolved", "completed", "scheduled"}:
            continue
        if status not in {"investigating", "identified", "monitoring", "in_progress", "verifying"}:
            raise ValueError("Unknown incident status")
        affected = item.get("components", [])
        if not affected:
            logger.warning("Unclassified status incident: %s", item["id"])
        if not any(c["id"] in ids for c in affected):
            continue
        incidents.append(dict(id=item["id"], title=item["name"], status=status,
            url=safe_url(item.get("shortlink"), provider["status_url"]),
            updated_at=item.get("updated_at"), confirmed=True))
    affected = [c["name"] for c in selected if c["status"] != "operational"]
    return dict(reported_status="disruption" if incidents or affected else "no_incidents",
                affected_components=affected, incidents=incidents)


class FeedDescription(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []
        self.components = []
        self.in_li = False

    def handle_starttag(self, tag, attrs):
        if tag == "li":
            self.in_li = True
            self.components.append("")

    def handle_endtag(self, tag):
        if tag == "li":
            self.in_li = False
        self.text.append("\n")

    def handle_data(self, data):
        self.text.append(data)
        if self.in_li:
            self.components[-1] += data


def hashicorp_rss(payload, provider):
    # Reject DTDs; the public feed requires neither entities nor external resources.
    if b"<!DOCTYPE" in payload.upper() or b"<!ENTITY" in payload.upper():
        raise ValueError("Unsupported XML declaration")
    root = ElementTree.fromstring(payload)
    channel = root.find("channel")
    if root.tag != "rss" or channel is None:
        raise ValueError("Invalid RSS feed")
    incidents, seen, unclassified = [], [], {}
    for item in channel.findall("item"):
        identity = item.findtext("guid") or item.findtext("link")
        if not identity:
            raise ValueError("Incident has no identity")
        description = FeedDescription()
        description.feed(item.findtext("description") or "")
        match = re.search(r"Status:[ \t]*([A-Za-z_ ]+)", "".join(description.text))
        status = match.group(1).strip().lower() if match else ""
        if status in {"resolved", "complete", "completed", "scheduled"}:
            # Resolution must clear a previously tracked incident even when its
            # latest update no longer includes affected-component metadata.
            seen.append(identity)
            continue
        names = [re.sub(r"\s*\([^()]*\)\s*$", "", c).strip() for c in description.components]
        if not names:
            unclassified[identity] = hashlib.sha256(ElementTree.tostring(item)).hexdigest()
        if not set(names).intersection(provider["components"]):
            continue
        if status not in {"investigating", "identified", "monitoring", "in progress", "in_progress", "verifying"}:
            raise ValueError("Unknown RSS incident status")
        seen.append(identity)
        incidents.append(dict(id=identity, title=item.findtext("title") or "Service incident",
            status=status, url=safe_url(item.findtext("link"), provider["status_url"]),
            updated_at=item.findtext("pubDate"), confirmed=True))
    key = (provider["id"], provider["feed_url"])
    previous = _rss_unclassified.get(key, {})
    for identity, fingerprint in unclassified.items():
        if previous.get(identity) != fingerprint:
            logger.warning("Unclassified HashiCorp incident: %s", identity)
    _rss_unclassified[key] = unclassified
    return dict(reported_status="disruption" if incidents else "no_incidents",
                affected_components=provider["components"] if incidents else [], incidents=incidents,
                seen_ids=seen)


ADAPTERS = {"statuspage": statuspage, "hashicorp_rss": hashicorp_rss}


def fetch(provider):
    request = Request(provider["feed_url"], headers={"User-Agent": "MC-Hub service status monitor"})
    with urlopen(request, timeout=10) as response:
        payload = response.read(2_000_001)
    if len(payload) > 2_000_000:
        raise ValueError("Status feed too large")
    return ADAPTERS[provider["adapter"]](payload, provider)


def poll_once():
    for provider in providers():
        attempted = now()
        try:
            snapshot = fetch(provider)
            ok = True
        except Exception:
            logger.exception("Status check failed for %s", provider["id"])
            snapshot, ok = None, False
        try:
            row = db.session.get(ServiceStatusSnapshot, provider["id"])
            if row is None:
                row = ServiceStatusSnapshot(provider=provider["id"])
                db.session.add(row)
            row.last_attempt_at, row.last_attempt_ok = attempted, ok
            if ok:
                if "seen_ids" in snapshot:
                    seen = set(snapshot.pop("seen_ids"))
                    for previous in (row.snapshot or {}).get("incidents", []):
                        if previous["id"] not in seen:
                            snapshot["incidents"].append({**previous, "confirmed": False})
                    if snapshot["incidents"]:
                        snapshot["reported_status"] = "disruption"
                if row.snapshot != snapshot:
                    logger.info("Service status changed for %s: %s", provider["id"], snapshot["reported_status"])
                row.snapshot, row.last_success_at = snapshot, now()
            db.session.commit()
        except Exception:
            db.session.rollback()
            logger.exception("Could not save status for %s", provider["id"])
        finally:
            db.session.remove()


def read_status():
    result = []
    for provider in providers():
        row = db.session.get(ServiceStatusSnapshot, provider["id"])
        success = row.last_success_at if row else None
        snapshot = row.snapshot if row and row.snapshot else dict(reported_status="unknown", incidents=[], affected_components=[])
        result.append({**snapshot, "provider": provider["id"], "name": provider["name"],
            "status_url": provider["status_url"],
            "freshness": "unknown" if success is None else "stale" if now() - success >= STALE_SECONDS else "fresh",
            "last_success_at": iso(success), "last_attempt_at": iso(row.last_attempt_at) if row else None,
            "last_attempt_ok": row.last_attempt_ok if row else None})
    return {"providers": result}
