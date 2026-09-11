"""AWS discovery and final-state feasibility under MC Hub's deployment contract.

On-Demand only; one 20 GiB gp2 root disk per instance plus tagged gp2 data disks; one EIP for any of
proxy/login/dtn. No Terraform template or plan inspection is performed.
"""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from functools import cached_property
from hashlib import sha256
import json
import logging
import re
from threading import Condition
from time import monotonic

import boto3
from marshmallow import ValidationError
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from cachetools import TTLCache, cached

from .openstack_manager import TAG_MINIMUM_REQUIREMENTS
from .project import AWSEnv
from ...exceptions.invalid_usage_exception import InvalidUsageException


PUBLIC_TAGS = {"proxy", "login", "dtn"}
RESERVATION_STATES = {"assessing", "scheduled", "pending", "active", "delayed"}
IMAGE_OWNERS = ["764336703387", "792107900819"]  # AlmaLinux and Rocky Linux
# IDs linked from the AWS On-Demand quota table:
# https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-on-demand-instances.html
ON_DEMAND_QUOTA_CODES = {
    **dict.fromkeys("ACDHIMRTZ", "L-1216C47A"),
    "DL": "L-6E869C2A", "F": "L-74FC7D96",
    "G": "L-DB2E81BA", "VT": "L-DB2E81BA",
    "HPC": "L-F7808C92", "U": "L-43DA4232", "INF": "L-1945791B",
    "P": "L-417A185B", "TRN": "L-2C3B7624", "X": "L-7295265B",
}
CATALOG_CACHE = TTLCache(maxsize=256, ttl=300)
CATALOG_CONDITION = Condition()
PRICE_CACHE = TTLCache(maxsize=128, ttl=86400)
PRICE_CONDITION = Condition()
logger = logging.getLogger(__name__)


def aws_call(call, **kwargs):
    try:
        return call(**kwargs)
    except (ClientError, BotoCoreError) as exc:
        code = exc.response["Error"]["Code"] if isinstance(exc, ClientError) else type(exc).__name__
        # Do not log credentials or raw provider responses.
        raise InvalidUsageException(
            f"AWS could not complete {call.__name__} ({code}). Check the project's credentials, permissions and region.",
            status_code=503,
        ) from exc


class AWSManager:
    def __init__(self, project, *, resource_ids=None, session=None):
        self.project = project
        self.resource_ids = resource_ids or {}
        self._zone_offerings = {}
        self._use_catalog_cache = True
        try:
            env = AWSEnv().load(project.env)
        except (ValidationError, TypeError) as exc:
            raise InvalidUsageException("Configure AWS access credentials and select a region in the project settings.") from exc
        # Credential changes (including session tokens) and regions never share entries.
        self._catalog_scope = sha256(json.dumps(env, sort_keys=True).encode()).hexdigest()
        self.session = session or boto3.Session(
            aws_access_key_id=env["AWS_ACCESS_KEY_ID"],
            aws_secret_access_key=env["AWS_SECRET_ACCESS_KEY"],
            aws_session_token=env.get("AWS_SESSION_TOKEN") or None,
            region_name=env["AWS_DEFAULT_REGION"],
        )
        config = Config(connect_timeout=5, read_timeout=15, retries={"mode": "standard", "max_attempts": 3})
        self.ec2 = self.session.client("ec2", config=config)
        self.sq = self.session.client("service-quotas", config=config)

    def pages(self, client, operation, key, **kwargs):
        # Explicit token loop also works with non-paginated EC2 operations.
        result = []
        while True:
            page = aws_call(getattr(client, operation), **kwargs)
            result.extend(page.get(key, []))
            token = page.get("NextToken")
            if not token:
                return result
            kwargs["NextToken"] = token

    def regions(self):
        return sorted(r["RegionName"] for r in aws_call(self.ec2.describe_regions)["Regions"])

    @cached(cache=CATALOG_CACHE, condition=CATALOG_CONDITION,
            key=lambda self, operation, key, params: (self._catalog_scope, operation, key, params))
    def _cached_catalog(self, operation, key, params):
        return self.pages(self.ec2, operation, key, **json.loads(params))

    def catalog(self, operation, key, **kwargs):
        if not self._use_catalog_cache:
            return self.pages(self.ec2, operation, key, **kwargs)
        return deepcopy(self._cached_catalog(operation, key, json.dumps(kwargs, sort_keys=True)))

    def validate_project(self):
        if self.project.env["AWS_DEFAULT_REGION"] not in self.regions():
            raise InvalidUsageException("Select a region enabled for this AWS account.")
        # Always exercise real reads at project save, even with a warm catalog.
        self._use_catalog_cache = False
        try:
            self.prices = self.read_prices()  # Verify permission even with a warm cache.
            with PRICE_CONDITION:
                PRICE_CACHE[self._catalog_scope] = self.prices
            self.images
            self.availability_zones
            self.types
            self.budget
        finally:
            self._use_catalog_cache = True

    def read_prices(self):
        client = self.session.client("pricing", region_name="us-east-1",
                                     config=Config(connect_timeout=5, read_timeout=15,
                                                   retries={"mode": "standard", "max_attempts": 2}))
        filters = {"regionCode": self.project.env["AWS_DEFAULT_REGION"],
                   "productFamily": "Compute Instance", "operatingSystem": "Linux",
                   "tenancy": "Shared", "preInstalledSw": "NA", "capacitystatus": "Used",
                   "operation": "RunInstances"}
        products = self.pages(client, "get_products", "PriceList", ServiceCode="AmazonEC2",
                              MaxResults=100, Filters=[{"Type": "TERM_MATCH", "Field": k, "Value": v}
                                                       for k, v in filters.items()])
        prices = {}
        for raw in products:
            product = json.loads(raw)
            attrs = product.get("product", {}).get("attributes", {})
            name = attrs.get("instanceType")
            if not name or any(attrs.get(k) != v for k, v in filters.items() if k != "productFamily"):
                continue
            for term in product.get("terms", {}).get("OnDemand", {}).values():
                for dimension in term.get("priceDimensions", {}).values():
                    if (dimension.get("unit") != "Hrs" or dimension.get("beginRange") != "0"
                            or dimension.get("endRange") != "Inf"):
                        continue
                    try:
                        rate = Decimal(dimension["pricePerUnit"]["USD"])
                    except (KeyError, InvalidOperation):
                        continue
                    if rate.is_finite() and rate > 0:
                        # Conflicting matches must never silently understate the rate.
                        prices[name] = max(prices.get(name, rate), rate)
        return prices

    @cached(cache=PRICE_CACHE, condition=PRICE_CONDITION, key=lambda self: self._catalog_scope)
    def cached_prices(self):
        started = monotonic()
        try:
            return self.read_prices()
        finally:
            logger.info("AWS discovery source=prices region=%s duration=%.3fs",
                        self.project.env["AWS_DEFAULT_REGION"], monotonic() - started)

    @cached_property
    def prices(self):
        return self.cached_prices()

    def price_issue(self, instance_type):
        ceiling = getattr(self.project, "max_instance_hourly_price", None)
        if ceiling is None:
            return None
        price = instance_type.get("hourly_price_usd")
        if price is None:
            return {"code": "instance_price", "message": f"{instance_type['name']}: hourly price is unavailable; the project price limit cannot be verified."}
        if Decimal(str(price)) > Decimal(str(ceiling)):
            return {"code": "instance_price", "message": f"{instance_type['name']}: ${price}/hour exceeds the project's ${ceiling}/hour per-instance limit (USD)."}
        return None

    @cached_property
    def availability_zones(self):
        zones = self.catalog("describe_availability_zones", "AvailabilityZones", Filters=[
            {"Name": "region-name", "Values": [self.project.env["AWS_DEFAULT_REGION"]]},
            {"Name": "zone-type", "Values": ["availability-zone"]},
            {"Name": "state", "Values": ["available"]},
        ])
        return sorted(z["ZoneName"] for z in zones
                      if z.get("RegionName") == self.project.env["AWS_DEFAULT_REGION"]
                      and z.get("ZoneType") == "availability-zone"
                      and z.get("State") == "available"
                      and z.get("OptInStatus") in {"opt-in-not-required", "opted-in"})

    def zone_issues(self, definition):
        zone = definition.get("availability_zone")
        if not self.availability_zones:
            return [{"code": "availability_zone", "message": "AWS returned no available standard zones in the project's region."}]
        if zone not in (None, "") and zone not in self.availability_zones:
            return [{"code": "availability_zone", "message": "Select an available zone in the project's AWS region, or leave it unset."}]
        return []

    def offered_in_zone(self, zone):
        if zone not in self._zone_offerings:
            self._zone_offerings[zone] = {
                t["InstanceType"] for t in self.catalog(
                    "describe_instance_type_offerings", "InstanceTypeOfferings",
                    LocationType="availability-zone", Filters=[{"Name": "location", "Values": [zone]}],
                )
            }
        return self._zone_offerings[zone]

    @cached_property
    def offered_in_all_zones(self):
        zones = self.availability_zones
        if not zones:
            return set()
        # Each zone's offerings use the shared catalog cache; fetch cold entries
        # concurrently rather than adding one sequential request per zone.
        with ThreadPoolExecutor(max_workers=min(4, len(zones))) as executor:
            offerings = list(executor.map(self.offered_in_zone, zones))
        return set.intersection(*offerings)

    def offered_for_definition(self, definition):
        if self.zone_issues(definition):
            return set()
        zone = definition.get("availability_zone")
        return self.offered_in_zone(zone) if zone else self.offered_in_all_zones

    @cached_property
    def quotas_by_name(self):
        # Listing entire services is expensive even on an otherwise warm request.
        # Only request the pools represented by this region's instance offerings.
        required = {("ebs", "L-D18FCD1D"), ("ec2", "L-0263D0A3")}
        for name in self.regional_offerings.intersection(self.all_types):
            prefix = re.match(r"[a-z]+", name)
            code = ON_DEMAND_QUOTA_CODES.get(prefix[0].upper()) if prefix else None
            if code:
                required.add(("ec2", code))

        def read(service, code):
            started = monotonic()
            try:
                quotas = self.pages(self.sq, "list_service_quotas", "Quotas",
                                    ServiceCode=service, QuotaCode=code)
                quota = next((q for q in quotas if q.get("QuotaCode") == code), None)
                if quota is None or "Value" not in quota or quota.get("ErrorReason"):
                    raise InvalidUsageException(f"AWS did not return the applied quota {service}/{code}.", status_code=503)
                return quota["QuotaName"], quota["Value"]
            finally:
                logger.info("AWS quota service=%s code=%s duration=%.3fs", service, code, monotonic() - started)

        with ThreadPoolExecutor(max_workers=3) as executor:
            pending = [executor.submit(read, service, code) for service, code in sorted(required)]
            return dict(future.result() for future in pending)

    @cached_property
    def pools(self):
        pools = {}
        for name, value in self.quotas_by_name.items():
            if name.startswith("Running On-Demand "):
                pools[name.removeprefix("Running On-Demand ").removesuffix(" instances")] = value
        if not pools:
            raise InvalidUsageException("AWS did not return the applied On-Demand quotas.", status_code=503)
        return pools

    def pool_for(self, name):
        family = name.split(".")[0]
        prefix = re.match(r"[a-z]+", family)
        prefix = prefix[0].upper() if prefix else ""
        for pool in self.pools:
            if pool.startswith("Standard ("):
                families = pool.split("(", 1)[1].rstrip(")").replace(" ", "").split(",")
            elif pool == "High Memory":
                families = ["U"]
            else:
                families = pool.split(" and ")
            if prefix in families:
                return pool
        return None

    @cached_property
    def all_types(self):
        return {t["InstanceType"]: t for t in self.catalog("describe_instance_types", "InstanceTypes")}

    @cached_property
    def regional_offerings(self):
        return {t["InstanceType"] for t in self.catalog(
            "describe_instance_type_offerings", "InstanceTypeOfferings", LocationType="region"
        )}

    @cached_property
    def types(self):
        offered = self.regional_offerings
        result = []
        for name, t in self.all_types.items():
            pool = self.pool_for(name)
            if (name not in offered or pool is None or t.get("BareMetal")
                    or "on-demand" not in t.get("SupportedUsageClasses", [])
                    or "x86_64" not in t["ProcessorInfo"]["SupportedArchitectures"]
                    or "hvm" not in t.get("SupportedVirtualizationTypes", [])
                    or "ebs" not in t.get("SupportedRootDeviceTypes", [])):
                continue
            result.append({"name": name, "vcpus": t["VCpuInfo"]["DefaultVCpus"],
                           "ram": t["MemoryInfo"]["SizeInMiB"], "quota_pool": pool,
                           "required_volume_count": 1, "required_volume_size": 20,
                           "hourly_price_usd": str(self.prices[name]) if name in self.prices else None,
                           "gpus": [{"count": g.get("LogicalGpuCount") or g.get("Count") or None,
                                     **({"partition_size": g["GpuPartitionSize"]} if g.get("GpuPartitionSize") else {}),
                                     "manufacturer": g.get("Manufacturer", ""),
                                     "name": g.get("Name", "GPU"),
                                     "memory_mib": g.get("MemoryInfo", {}).get("SizeInMiB")}
                                    for g in t.get("GpuInfo", {}).get("Gpus", [])]})
        return sorted(result, key=lambda t: (Decimal(t["hourly_price_usd"]) if t["hourly_price_usd"] is not None else Decimal("Infinity"), t["ram"], t["vcpus"], t["name"]))

    @cached_property
    def images(self):
        images = self.catalog("describe_images", "Images", Owners=IMAGE_OWNERS, Filters=[
            {"Name": "name", "Values": ["AlmaLinux OS 9*", "Rocky-9-*", "Rocky-9.*"]},
            {"Name": "state", "Values": ["available"]},
            {"Name": "architecture", "Values": ["x86_64"]},
            {"Name": "virtualization-type", "Values": ["hvm"]},
            {"Name": "root-device-type", "Values": ["ebs"]},
        ])
        # The contract permits exactly one disk and cannot shrink a larger AMI.
        return sorted((im for im in images if len(im.get("BlockDeviceMappings", [])) == 1
                       and im["BlockDeviceMappings"][0].get("Ebs", {}).get("VolumeSize", 21) <= 20
                       and not im.get("ProductCodes")),
                      key=lambda im: im.get("CreationDate", ""), reverse=True)

    @cached_property
    def inventory(self):
        operations = {
            "instances": ("describe_instances", "Reservations"),
            "volumes": ("describe_volumes", "Volumes"),
            "addresses": ("describe_addresses", "Addresses"),
            "reservations": ("describe_capacity_reservations", "CapacityReservations"),
        }
        with ThreadPoolExecutor(max_workers=4) as executor:
            pending = {key: executor.submit(self.pages, self.ec2, *operation)
                       for key, operation in operations.items()}
            inventory = {key: future.result() for key, future in pending.items()}
        inventory["instances"] = [i for r in inventory["instances"] for i in r["Instances"]]
        return inventory

    def preload(self):
        """Read independent sources concurrently; quotas and usage remain fresh."""
        names = ("all_types", "regional_offerings", "quotas_by_name", "inventory", "images", "availability_zones")
        def read(name):
            started = monotonic()
            try:
                return getattr(self, name)
            finally:
                logger.info("AWS discovery source=%s region=%s duration=%.3fs", name,
                            self.project.env["AWS_DEFAULT_REGION"], monotonic() - started)
        with ThreadPoolExecutor(max_workers=6) as executor:
            pending = [executor.submit(read, name) for name in names if name not in self.__dict__]
            for future in pending:
                future.result()

    def vcpus(self, instance_type):
        if instance_type not in self.all_types:
            found = aws_call(self.ec2.describe_instance_types, InstanceTypes=[instance_type])["InstanceTypes"]
            self.all_types.update({t["InstanceType"]: t for t in found})
        return self.all_types[instance_type]["VCpuInfo"]["DefaultVCpus"]

    @cached_property
    def budget(self):
        limits = dict(self.pools)
        for key, pattern, factor in (
            ("gp2", "Storage for General Purpose SSD (gp2) volumes", 1024),
            ("eips", "EC2-VPC Elastic IPs", 1),
        ):
            found = [v for n, v in self.quotas_by_name.items() if n.startswith(pattern)]
            if not found:
                raise InvalidUsageException(f"AWS did not return the applied {key} quota.", status_code=503)
            limits[key] = found[0] * factor
        used, own = Counter(), Counter()
        inv = self.inventory
        reservation_ids = {r["CapacityReservationId"] for r in inv["reservations"]
                           if r["State"] in RESERVATION_STATES}
        for r in inv["reservations"]:
            if r["State"] in RESERVATION_STATES:
                pool = self.pool_for(r["InstanceType"])
                if pool:
                    used[pool] += r["TotalInstanceCount"] * self.vcpus(r["InstanceType"])
        for i in inv["instances"]:
            if i["State"]["Name"] != "running" or i.get("InstanceLifecycle") in {"spot", "capacity-block"}:
                continue
            pool = self.pool_for(i["InstanceType"])
            if not pool or i.get("CapacityReservationId") in reservation_ids:
                continue
            amount = self.vcpus(i["InstanceType"])
            used[pool] += amount
            if i["InstanceId"] in self.resource_ids.get("instances", []):
                own[pool] += amount
        for v in inv["volumes"]:
            if v["VolumeType"] == "gp2" and v["State"] not in {"deleted", "error"}:
                used["gp2"] += v["Size"]
                if v["VolumeId"] in self.resource_ids.get("volumes", []):
                    own["gp2"] += v["Size"]
        for a in inv["addresses"]:
            if a.get("PublicIpv4Pool", "amazon") == "amazon":
                used["eips"] += 1
                if a.get("AllocationId") in self.resource_ids.get("addresses", []):
                    own["eips"] += 1
        return {k: max(0, limit - used[k] + own[k]) for k, limit in limits.items()}

    def volume_demand(self, definition):
        demand, issues = Counter(), []
        volumes = definition.get("volumes", {})
        groups = definition.get("instances", {})
        if not isinstance(volumes, dict):
            return demand, [{"code": "volumes", "message": "Volumes must be grouped by instance tag."}]
        for tag, rows in volumes.items():
            if not isinstance(rows, dict):
                issues.append({"code": "volumes", "message": f"{tag}: invalid volume definitions."})
                continue
            count = sum(g["count"] for g in groups.values()
                        if isinstance(g, dict) and type(g.get("count")) is int and g["count"] > 0
                        and isinstance(g.get("tags"), list) and tag in g["tags"]) if isinstance(groups, dict) else 0
            for name, volume in rows.items():
                if (not isinstance(volume, dict) or set(volume) != {"size"}
                        or type(volume.get("size")) is not int or volume["size"] <= 0):
                    issues.append({"code": "volumes", "message": f"{tag}/{name}: specify a positive whole-number size in GiB; AWS data volumes use gp2."})
                    continue
                demand["gp2"] += count * volume["size"]
                if not count:
                    issues.append({"code": "volumes", "message": f"{tag}/{name}: no active instance has the {tag} tag."})
        return demand, issues

    def demand(self, definition, *, incomplete=False):
        demand, issues = Counter(), []
        groups = definition.get("instances", {})
        if not isinstance(groups, dict) or not groups:
            return demand, [{"code": "definition", "message": "Define at least one instance group."}]
        types = self.types_by_name
        for name, group in groups.items():
            if not isinstance(group, dict):
                issues.append({"code": "definition", "message": f"{name}: invalid instance group."})
                continue
            if set(group) - {"type", "count", "tags"}:
                issues.append({"code": "definition", "message": f"{name}: only type, count and tags are supported; AWS uses On-Demand instances with one 20 GiB gp2 root disk."})
            count, tags = group.get("count"), group.get("tags", [])
            if type(count) is not int or count < 0 or not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
                issues.append({"code": "definition", "message": f"{name}: use a nonnegative integer count and a list of tags."})
                continue
            demand["gp2"] += 20 * count
            demand["eips"] += count if PUBLIC_TAGS.intersection(tags) else 0
            if count == 0:
                continue
            selected_type = group.get("type")
            t = types.get(selected_type) if isinstance(selected_type, str) else None
            if t is None:
                if not incomplete or group.get("type"):
                    issues.append({"code": "instance_type", "message": f"{name}: select an available instance type."})
                continue
            price_issue = self.price_issue(t)
            if price_issue:
                issues.append({**price_issue, "message": f"{name}: {price_issue['message']}"})
            demand[t["quota_pool"]] += count * t["vcpus"]
            zone = definition.get("availability_zone")
            if not self.zone_issues(definition) and t["name"] not in self.offered_for_definition(definition):
                location = zone or "every available zone in the project's region"
                issues.append({"code": "instance_zone", "message": f"{name}: {t['name']} is not offered in {location}. Select another type or a specific zone that offers it."})
            image = next((i for i in self.images if i["ImageId"] == definition.get("image")), None)
            boot_mode = image.get("BootMode") if image else None
            if boot_mode in {"uefi", "legacy-bios"} and boot_mode not in self.all_types[t["name"]].get("SupportedBootModes", []):
                issues.append({"code": "image_type", "message": f"{name}: {t['name']} does not support the image's {boot_mode} boot mode."})
            for tag in tags:
                minimum = TAG_MINIMUM_REQUIREMENTS.get(tag)
                if minimum and (t["ram"] < minimum["ram"] or t["vcpus"] < minimum["vcpus"]):
                    issues.append({"code": "instance_type", "message": f"{name}: {t['name']} does not meet the {tag} role's requirements."})
                    break
        return demand, issues

    @cached_property
    def types_by_name(self):
        return {t["name"]: t for t in self.types}

    def quota_issues(self, demand):
        return [{"code": "quota_exceeded", "resource": k, "required": value,
                 "available": self.budget[k],
                 "message": f"{k}: this definition requires {value:g} {'GiB' if k == 'gp2' else 'Elastic IPs' if k == 'eips' else 'vCPUs'}; {self.budget[k]:g} are available for this cluster."}
                for k, value in demand.items() if value > self.budget[k]]

    def evaluate(self, definition):
        demand, issues = self.demand(definition)
        issues += self.zone_issues(definition)
        volume_demand, volume_issues = self.volume_demand(definition)
        demand.update(volume_demand)
        issues += volume_issues
        issues += self.quota_issues(demand)
        if definition.get("image") not in [i["ImageId"] for i in self.images]:
            issues.append({"code": "image", "message": "Select an available AlmaLinux 9 or Rocky Linux 9 x86_64 image."})
        return {"status": "blocked" if issues else "ready", "issues": issues,
                "checked_at": datetime.now(timezone.utc).isoformat(), "scope": "final_state"}

    def choices(self, definition):
        choices = {}
        groups = definition.get("instances", {})
        if not isinstance(groups, dict):
            return choices
        if self.zone_issues(definition):
            return {name: [] for name in groups}
        volume_demand, _ = self.volume_demand(definition)
        offered = self.offered_for_definition(definition)
        for name, group in groups.items():
            choices[name] = []
            if not isinstance(group, dict):
                continue
            others = deepcopy(definition)
            del others["instances"][name]
            other_demand, _ = self.demand(others, incomplete=True)
            for t in self.types:
                if t["name"] not in offered or self.price_issue(t):
                    continue
                candidate = {"instances": {name: {**group, "type": t["name"]}},
                             "image": definition.get("image"), "availability_zone": definition.get("availability_zone")}
                demand, issues = self.demand(candidate, incomplete=True)
                demand.update(other_demand)
                demand.update(volume_demand)
                if not issues and not self.quota_issues(demand):
                    choices[name].append(t["name"])
        return choices

    def editor_resources(self, definition):
        self.preload()
        # Assign defaults sequentially against one AWS snapshot, without a browser
        # round trip (and new inventory scan) for every empty group.
        completed = deepcopy(definition)
        defaults = {}
        groups = completed.get("instances", {})
        if isinstance(groups, dict):
            for name, group in groups.items():
                if isinstance(group, dict) and not group.get("type"):
                    choices = self.choices(completed).get(name, [])
                    if choices:
                        group["type"] = defaults[name] = choices[0]
        return {"feasibility": self.evaluate(completed),
                "instance_choices": self.choices(completed), "instance_defaults": defaults}

    @property
    def available_resources(self):
        self.preload()
        affordable = [t for t in self.types if t["name"] in self.offered_in_all_zones and not self.price_issue(t) and t["vcpus"] <= self.budget[t["quota_pool"]] and self.budget["gp2"] >= 20]
        return {"provider": "aws", "region": self.project.env["AWS_DEFAULT_REGION"], "quotas": {},
                "possible_resources": {"image": [i["ImageId"] for i in self.images],
                    "availability_zone": self.availability_zones,
                    "types": [t["name"] for t in affordable], "tag_types": {}, "volumes": {}},
                "resource_details": {"instance_types": self.types,
                    "images": [{"id": i["ImageId"], "name": i["Name"]} for i in self.images]}}


def ensure_aws_feasible(project, definition, resource_ids=None):
    if project.provider != "aws":
        return
    result = AWSManager(project, resource_ids=resource_ids).evaluate(definition)
    if result["status"] != "ready":
        raise InvalidUsageException(" ".join(i["message"] for i in result["issues"]), status_code=422)
