import time
import datetime
import secrets
import github
import requests
import json
import logging
from cachetools import cached, TTLCache

import base64
import yaml

from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.serialization import pkcs7
from cryptography import x509
from cryptography.x509.oid import NameOID

import humanize

from marshmallow import ValidationError
from sqlalchemy.sql import except_, func
from sqlalchemy.exc import IntegrityError

from mchub.models.cloud.cloud_manager import CloudManager
from mchub.models.magic_castle.terraform_cloud_status import TFCloudStatusCode

from .magic_castle_configuration import MagicCastleConfiguration
from .cluster_status_code import ClusterStatusCode

from ..terraform_cloud import TerraformCloudRunORM
from ..terraform.terraform_plan_parser import TerraformPlanParser
from ..terraform.terraform_state import TerraformState
from ..cloud.dns_manager import DnsManager
from ..cloud.project import Project
from ..puppet.provisioning_manager import ProvisioningManager, MAX_PROVISIONING_TIME

from ...configuration.magic_castle import (
    MAIN_TERRAFORM_FILENAME,
    TERRAFORM_STATE_FILENAME,
    MAGIC_CASTLE_PATH,
)
from ...configuration.env import CLUSTERS_PATH

from ...exceptions.invalid_usage_exception import (
    ClusterNotFoundException,
    ClusterExistsException,
    InvalidPlanParameters,
    InvalidUsageException,
    BusyClusterException,
    PlanNotCreatedException,
    RunIDNotSet,
)
from ...exceptions.server_exception import (
    PlanException,
    TerraformCloudException,
)

from ...database import db

from ...configuration import get_config
from ...services.terraform_cloud_api import get_terraform_cloud, TerraformCloudVariable
from ...services.github_api import get_github_storage


def _encrypt_eyaml(value: str, cert_pem: str) -> str:
    cert = x509.load_pem_x509_certificate(cert_pem.encode())
    encrypted_der = (
        pkcs7.PKCS7EnvelopeBuilder()
        .set_data(value.encode())
        .add_recipient(cert)
        .encrypt(serialization.Encoding.DER, [])
    )
    return f"ENC[PKCS7,{base64.b64encode(encrypted_der).decode()}]"


def _hieradata_to_entries(hieradata: str) -> list:
    """Parse a hieradata YAML string into a list of {key, value, encrypt} dicts.
    ENC[...] values are masked (value=None, encrypt=True)."""
    if not hieradata or not hieradata.strip():
        return []
    try:
        parsed = yaml.safe_load(hieradata)
    except yaml.YAMLError:
        return []
    if not isinstance(parsed, dict):
        return []

    entries = []
    for key, value in parsed.items():
        if isinstance(value, str) and value.startswith("ENC["):
            entries.append({"key": key, "value": None, "encrypt": True})
        elif isinstance(value, bool):
            entries.append({"key": key, "value": "true" if value else "false", "encrypt": False})
        elif isinstance(value, (int, float)):
            entries.append({"key": key, "value": str(value), "encrypt": False})
        elif isinstance(value, str):
            entries.append({"key": key, "value": value, "encrypt": False})
        else:
            entries.append({"key": key, "value": yaml.dump(value, default_flow_style=True).strip(), "encrypt": False})
    return entries


def _entries_to_hieradata(entries: list, existing_hieradata: str, eyaml_public_key: str) -> str:
    """Convert a list of {key, value, encrypt} entries to a hieradata YAML string."""
    existing = {}
    if existing_hieradata:
        try:
            parsed = yaml.safe_load(existing_hieradata)
            if isinstance(parsed, dict):
                existing = parsed
        except yaml.YAMLError:
            pass

    result = {}
    for entry in entries:
        key = entry.get("key", "").strip()
        if not key:
            continue
        value = entry.get("value")
        encrypt = entry.get("encrypt", False)

        if encrypt and value is None:
            if key in existing:
                result[key] = existing[key]
        elif encrypt and value is not None and eyaml_public_key:
            result[key] = _encrypt_eyaml(str(value), eyaml_public_key)
        elif not encrypt and value is not None:
            try:
                result[key] = yaml.safe_load(str(value))
            except yaml.YAMLError:
                result[key] = str(value)

    if not result:
        return ""
    return yaml.dump(result, default_flow_style=False, allow_unicode=True).rstrip()


def _generate_eyaml_keypair():
    """Generate an RSA-2048 key pair and self-signed certificate for eyaml encryption.
    Returns (private_key_pem, certificate_pem) as strings."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, u"mchub-eyaml")])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.utcnow())
        .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=3650))
        .sign(private_key, hashes.SHA256())
    )
    private_key_pem = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    ).decode()
    cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode()
    return private_key_pem, cert_pem


TERRAFORM_PLAN_BINARY_FILENAME = "terraform_plan"
TERRAFORM_APPLY_LOG_FILENAME = "terraform_apply.log"
TERRAFORM_PLAN_LOG_FILENAME = "terraform_plan.log"
logger = logging.getLogger(__name__)


class MagicCastleORM(db.Model):
    __tablename__ = "magiccastle"
    id = db.Column(db.Integer, primary_key=True)
    hostname = db.Column(db.String(256), unique=True, nullable=False)

    tfcloud_workspace = db.Column(db.String(256))
    cluster_token = db.Column(db.String(64), unique=True)
    tfcloud_run = db.relationship(
        "TerraformCloudRunORM",
        back_populates="magic_castle",
        cascade="all, delete-orphan",
        uselist=False,
    )

    status = db.Column(db.Enum(ClusterStatusCode), default=ClusterStatusCode.NOT_FOUND)
    creation_step = db.Column(db.String(32))
    deployment_started_at = db.Column(db.DateTime())
    undeployed = db.Column(db.Boolean(), nullable=False, default=False, server_default="0")
    created = db.Column(db.DateTime(), default=func.now())
    expiration_date = db.Column(db.String(32))
    config = db.Column(db.PickleType())
    applied_config = db.Column(db.PickleType())
    eyaml_public_key = db.Column(db.Text)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    project_id = db.Column(db.Integer, db.ForeignKey("project.id"))
    project = db.relationship(
        "Project",
        back_populates="magic_castles",
        uselist=False,
        cascade_backrefs=False,
    )


@cached(cache=TTLCache(maxsize=1024, ttl=10))
def get_tf_status_cache(run_id):
    tf = get_terraform_cloud()
    return tf.get_run_status(run_id)


class MagicCastle:
    """
    Magic Castle is the class that manages everything related to the state of a Magic Castle cluster.
    It is responsible for building, modifying and destroying the cluster using Terraform.
    It is also used to get the state of the cluster and the cloud resources available.

    Note: In this class, the database connection is recreated everytime the database must be accessed
    to avoid using the same connection in multiple threads (which doesn't work with sqlite).
    """

    __slots__ = ["orm", "_service_statuses"]

    def __init__(self, orm=None):
        self._service_statuses = None
        if orm:
            self.orm = orm
        else:
            self.orm = MagicCastleORM(
                status=ClusterStatusCode.NOT_FOUND,
                config={},
                tfcloud_run=TerraformCloudRunORM(),
            )

    @property
    def hostname(self):
        return self.orm.hostname

    @property
    def domain(self):
        return self.config.domain

    @property
    def tfcloud_workspace(self):
        return self.orm.tfcloud_workspace

    @property
    def cluster_token(self):
        return self.orm.cluster_token

    @property
    def tfcloud_run(self):
        return self.orm.tfcloud_run

    @property
    def cloud_id(self):
        return self.orm.project.id

    @property
    def project(self):
        return self.orm.project

    @property
    def expiration_date(self):
        return self.orm.expiration_date

    @property
    def age(self):
        now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        delta = now - self.orm.created
        return humanize.naturaldelta(delta)

    @property
    def config(self):
        return self.orm.config

    @config.setter
    def config(self, value):
        self.orm.config = value

    @property
    def applied_config(self):
        return self.orm.applied_config

    def set_configuration(self, configuration: dict):
        logger.debug(f"Call <{self.__class__.__name__}>:set_configuration")

        expect_tf_changes = False
        self.orm.expiration_date = configuration.pop("expiration_date", None)
        cloud_id = configuration.pop("cloud")["id"]

        hieradata_entries = configuration.pop("hieradata_entries", None)
        if hieradata_entries is not None:
            existing_hieradata = self.config.get("hieradata", "") if self.config else ""
            configuration["hieradata"] = _entries_to_hieradata(
                hieradata_entries, existing_hieradata, self.orm.eyaml_public_key
            )

        if self.orm.project is None or self.orm.project.id != cloud_id:
            self.orm.project = db.session.get(Project, cloud_id)
            expect_tf_changes = True
        try:
            config = MagicCastleConfiguration(self.orm.project.provider, configuration)
        except ValidationError as err:
            raise InvalidUsageException(
                f"The magic castle configuration could not be parsed.\nError: {err.messages}"
            )
        if self.config != config:
            self.config = config
            self.orm.hostname = f"{self.config.cluster_name}.{self.config.domain}"
            expect_tf_changes = True
        return expect_tf_changes

    def _update_status_from_tf_cloud(self):
        """
        Fetch all the updates from the Terraform Cloud api if the run_id is started,
        otherwise get status from db.
        This update the status, plan, apply log and tf_state
        """
        if self.orm.status == ClusterStatusCode.NOT_DEPLOYED:
            return
        if self.tfcloud_run.run_id:
            # Update status from Terraform Cloud
            try:
                tf_status, is_destroy = get_tf_status_cache(self.tfcloud_run.run_id)
            except TerraformCloudException as e:
                logger.error(
                    f"Error on {self.orm.tfcloud_workspace}, error={e.message}"
                )
                return self.orm.status

            if tf_status is not None and is_destroy is not None:
                status = ClusterStatusCode.from_tfcloudstatus(
                    tf_status, is_destroy
                )
                # Terraform Cloud can report a completed plan before its plan
                # JSON is available. Keep clients polling until the plan has
                # actually been persisted locally.
                if status == ClusterStatusCode.CREATED and self.plan is None:
                    status = ClusterStatusCode.PLAN_RUNNING
                provisioning_is_complete = (
                    self.orm.status == ClusterStatusCode.PROVISIONING_SUCCESS
                )
                if not (
                    status == ClusterStatusCode.PROVISIONING_RUNNING
                    and provisioning_is_complete
                ):
                    if status == ClusterStatusCode.DESTROY_SUCCESS:
                        self.complete_teardown()
                        return
                    self.status = status

            # Fetch the apply_log
            if self.plan and not self.apply_url:
                tf = get_terraform_cloud()
                apply_url = tf.get_run_apply_log(self.tfcloud_run.run_id)
                logger.info(f"Update apply log for {self.tfcloud_run.run_id=}")
                self.apply_url = apply_url

            # Fetch the tf state
            if self.tf_state is None and ClusterStatusCode.is_provisioning(
                self.orm.status
            ):
                tf = get_terraform_cloud()
                tf_state = tf.get_tf_state(self.orm.tfcloud_workspace)
                if tf_state is not None:
                    self.tf_state = TerraformState(tf_state)
                    logger.info(f"Update tf_state {self.tfcloud_run.run_id=}")

    @property
    def status(self) -> ClusterStatusCode:
        if self.orm.status == ClusterStatusCode.BACKGROUND_TASK_RUNNING:
            return ClusterStatusCode.PLAN_RUNNING

        self._update_status_from_tf_cloud()

        # Older initial plans predate the unified undeployed lifecycle. Verify
        # remotely: a modification plan can also have no locally cached state.
        if (
            self.orm.status == ClusterStatusCode.CREATED
            and not self.orm.undeployed
            and self.orm.deployment_started_at is None
            and self.applied_config is None
            and self.tf_state is None
            and self.tfcloud_workspace
            and not get_terraform_cloud().workspace_has_state(self.tfcloud_workspace)
        ):
            self.orm.undeployed = True

        if self.orm.status == ClusterStatusCode.PROVISIONING_RUNNING:
            now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
            if self.services_are_online:
                self.status = ClusterStatusCode.PROVISIONING_SUCCESS
            elif MAX_PROVISIONING_TIME < (now - (self.orm.deployment_started_at or self.orm.created)).total_seconds():
                self.status = ClusterStatusCode.PROVISIONING_ERROR
        elif self.orm.status == ClusterStatusCode.DESTROY_SUCCESS:
            self.complete_teardown()

        db.session.commit()
        return self.orm.status

    @property
    def service_statuses(self):
        if self._service_statuses is None:
            self._service_statuses = ProvisioningManager.check_services(self.hostname)
        return self._service_statuses

    @property
    def services_are_online(self):
        return all(
            ProvisioningManager.service_is_healthy(service)
            for service in self.service_statuses.values()
        )

    @property
    def health(self):
        if self.orm.status != ClusterStatusCode.PROVISIONING_SUCCESS:
            return "unknown"
        return ProvisioningManager.get_health(self.service_statuses)

    @status.setter
    def status(self, status: ClusterStatusCode):
        if status != self.orm.status:
            self.orm.status = status
            db.session.commit()

    @tfcloud_run.setter
    def tfcloud_run(self, tfcloud_run: TerraformCloudRunORM):
        self.orm.tfcloud_run = tfcloud_run

    @property
    def plan(self) -> dict:
        return self.orm.tfcloud_run.plan

    @plan.setter
    def plan(self, plan: dict):
        self.orm.tfcloud_run.plan = plan
        db.session.commit()

    @property
    def tf_state(self) -> TerraformState:
        return self.orm.tfcloud_run.tf_state

    @tf_state.setter
    def tf_state(self, tf_state: TerraformState):
        self.orm.tfcloud_run.tf_state = tf_state

    @property
    def apply_url(self) -> str:
        return self.orm.tfcloud_run.apply_log_url

    @apply_url.setter
    def apply_url(self, apply_url: str):
        self.orm.tfcloud_run.apply_log_url = apply_url

    def get_progress(self):
        if self.apply_url and self.plan:
            res = requests.get(self.apply_url)
            apply_log = ""
            if res.status_code == 200:
                apply_log = res.text

            return TerraformPlanParser.get_done_changes(self.plan, apply_log)

    @property
    def state(self):
        status = self.status
        config = self.config if self.orm.undeployed else (self.applied_config or self.config)
        cloud = {"name": self.project.name, "id": self.project.id}
        return {
            **config,
            "undeployed": self.orm.undeployed,
            "hostname": self.hostname,
            "status": status,
            "health": self.health,
            "services": (
                self.service_statuses
                if status == ClusterStatusCode.PROVISIONING_SUCCESS
                else {}
            ),
            "freeipa_passwd": self.freeipa_passwd,
            "age": self.age,
            "expiration_date": self.expiration_date,
            "cloud": cloud,
            "hieradata_entries": _hieradata_to_entries(config.get("hieradata", "")),
        }

    @property
    def freeipa_passwd(self):
        if self.tf_state is not None:
            return self.tf_state.freeipa_passwd
        else:
            return None

    @property
    def allocated_resources(self):
        if self.is_busy:
            raise BusyClusterException

        if self.tf_state is not None:
            return dict(
                pre_allocated_instance_count=self.tf_state.instance_count,
                pre_allocated_ram=self.tf_state.ram,
                pre_allocated_cores=self.tf_state.cores,
                pre_allocated_volume_count=self.tf_state.volume_count,
                pre_allocated_volume_size=self.tf_state.volume_size,
            )
        else:
            return dict(
                pre_allocated_instance_count=0,
                pre_allocated_ram=0,
                pre_allocated_cores=0,
                pre_allocated_volume_count=0,
                pre_allocated_volume_size=0,
            )

    @property
    def is_busy(self):
        return self.orm.status in [
            ClusterStatusCode.PLAN_RUNNING,
            ClusterStatusCode.BUILD_RUNNING,
            ClusterStatusCode.DESTROY_RUNNING,
        ]

    @property
    def found(self):
        return self.status != ClusterStatusCode.NOT_FOUND

    def _get_var_tf(self):
        var_tf = self.config.get_var_tf()
        if self.cluster_token:
            mchub_url = get_config().get("mchub_url")
            tfe_token = self.cluster_token
            if self.orm.eyaml_public_key:
                tfe_token = _encrypt_eyaml(self.cluster_token, self.orm.eyaml_public_key)
            proxy_hieradata = (
                f"profile::slurm::controller::tfe_token: {tfe_token}\n"
                f"profile::slurm::controller::tfe_workspace: {self.tfcloud_workspace}\n"
                f"profile::slurm::controller::tfe_proxy_url: {mchub_url}/api/tfcloud-proxy"
            )
            existing = var_tf["hieradata"].strip()
            var_tf["hieradata"] = f"{existing}\n{proxy_hieradata}" if existing else proxy_hieradata
        return var_tf

    @staticmethod
    def validate_creation_version(data):
        if data.get("mc_version") not in get_github_storage().get_magic_castle_versions():
            raise InvalidUsageException("Invalid Magic Castle version")

    def validate_version_unchanged(self, data):
        existing_version = self.config.get("mc_version")
        if data.get("mc_version", existing_version) != existing_version:
            raise InvalidUsageException(
                "The Magic Castle version cannot be changed after plan creation"
            )

    def plan_creation(self, data, created_by_user_id=None):
        logger.debug(f"Call <{type(self).__name__}>:plan_creation")

        self.validate_creation_version(data)
        self.set_configuration(data)
        self.orm.created_by_user_id = created_by_user_id
        self.orm.undeployed = True
        self.orm.status = ClusterStatusCode.PLAN_RUNNING
        self.orm.creation_step = "github_repository"
        db.session.add(self.orm)
        try:
            db.session.commit()
        except IntegrityError:
            raise ClusterExistsException

        github_repo_fullname = get_github_storage().create_repo(
            self.hostname, self.project.github_template
        )

        workspace_name = self.config.cluster_name

        self.orm.creation_step = "terraform_workspace"
        db.session.commit()
        tf = get_terraform_cloud()
        workspace_id = tf.create_workspace(
            workspace_name, github_repo_fullname, self.orm.project.tfcloud_project_id
        )
        dns_envs = DnsManager(self.domain).get_environment_variables()
        terraform_vars = [TerraformCloudVariable(name=k, value=v, sensitive=True) for k, v in dns_envs.items()]
        terraform_vars.append(
            TerraformCloudVariable(name="pool", value="[]", sensitive=False, hcl=True, category="terraform")
        )

        eyaml_private_key, eyaml_public_key = _generate_eyaml_keypair()
        self.orm.eyaml_public_key = eyaml_public_key
        eyaml_private_key_b64 = base64.b64encode(eyaml_private_key.encode()).decode()
        terraform_vars.append(
            TerraformCloudVariable(name="tfc_eyaml_key", value=eyaml_private_key_b64, sensitive=True, category="terraform")
        )

        tf.set_workspace_variable_set(workspace_id, terraform_vars)

        mchub_url = get_config().get("mchub_url")
        if mchub_url:
            self.orm.cluster_token = secrets.token_urlsafe(32)

        self.orm.tfcloud_workspace = workspace_id

        logger.info(
            f"{self.hostname}: terraformcloud workspace=<{workspace_id}> created"
        )

        # Write the main terraform file to storage backend
        self.orm.creation_step = "variable_file"
        db.session.commit()
        try:
            var_tf = self._get_var_tf()
            github_commit = get_github_storage().write(var_tf, self.hostname)
        except Exception as error:
            self.delete()
            raise PlanException(
                "Could not write variables.tf on the storage backend.",
                additional_details=f"hostname: {self.hostname}, error: {error}",
            )
        logger.info(
            f"{self.hostname}: New commit <{github_commit}> on repo <{github_repo_fullname}>"
        )

        self.orm.creation_step = "resource_plan"
        db.session.commit()
        self.create_plan(github_sha=github_commit)
        db.session.commit()

    def plan_modification(self, data):
        logger.debug(f"Call <{self.__class__.__name__}>:plan_modification")

        if not self.found:
            raise ClusterNotFoundException
        if self.is_busy:
            raise BusyClusterException

        if self.orm.undeployed and (
            data.get("cluster_name", self.config.cluster_name) != self.config.cluster_name
            or data.get("domain", self.config.domain) != self.config.domain
            or data.get("cloud", {}).get("id", self.orm.project.id) != self.orm.project.id
        ):
            raise InvalidUsageException("Keep the existing hostname and cloud project when rebuilding a cluster")
        self.validate_version_unchanged(data)
        data["mc_version"] = self.config["mc_version"]

        config_changed = self.set_configuration(data)
        if self.orm.undeployed:
            # A saved configuration must never reuse a previously generated plan,
            # including when the next rebuild fails before creating its run.
            self.tfcloud_run = TerraformCloudRunORM()
            self.status = ClusterStatusCode.NOT_DEPLOYED
            db.session.commit()
            return

        # Check if main_file has changed before writing
        # and planning a change, some modifications may
        # only be reflected in the database and do not
        # require a plan.
        # Add an exception if the cluster is stuck in a destroy error
        if config_changed or self.status == ClusterStatusCode.DESTROY_ERROR:
            try:
                var_tf = self._get_var_tf()
                sha = get_github_storage().write(var_tf, self.hostname)
            except Exception as error:
                raise PlanException(
                    "Could not write variables.tf on the storage backend.",
                    additional_details=f"hostname: {self.hostname}, error: {error}",
                )
            self.create_plan(github_sha=sha)
            db.session.commit()

    def plan_destruction(self):
        logger.debug(f"Call <{self.__class__.__name__}:plan_destruction>")
        if self.is_busy:
            raise BusyClusterException

        if self.orm.tfcloud_workspace is None:
            if self.tf_state is not None:
                raise InvalidUsageException("Cannot tear down resources without the Terraform workspace")
            self.complete_teardown()
        else:
            tf = get_terraform_cloud()
            # A workspace whose initial plan failed has no state and therefore
            # has no managed resources to destroy. A destroy run would only
            # evaluate the same broken configuration and fail again.
            if not tf.workspace_has_state(self.orm.tfcloud_workspace):
                logger.info(
                    f"{self.hostname}: No Terraform state found; skipping destroy plan"
                )
                self.complete_teardown()
                return

            run_id = tf.destroy_plan(self.orm.tfcloud_workspace)
            logger.info(
                f"{self.hostname}: Apply destroy on workspace_id={self.orm.tfcloud_workspace} with run_id={run_id}"
            )
            self.create_plan(run_id=run_id)
            db.session.commit()

    def discard_teardown(self):
        if self.is_busy:
            raise BusyClusterException
        run_id = self.tfcloud_run.run_id
        if not run_id or not self.tfcloud_workspace:
            raise InvalidUsageException("No teardown plan to discard")
        tf = get_terraform_cloud()
        remote_status, is_destroy = tf.get_run_status(run_id)
        if not is_destroy:
            raise InvalidUsageException("Only a teardown plan can be discarded here")
        # Recover deployment details before dropping the destroy run, whose
        # creation replaced the locally cached deployment state.
        state = tf.get_tf_state(self.tfcloud_workspace)
        if state is None:
            raise InvalidUsageException("Could not restore the deployed cluster state")
        deployment_state = TerraformState(state)
        if remote_status != TFCloudStatusCode.DISCARDED:
            tf.discard_run(run_id)
        self.tfcloud_run = TerraformCloudRunORM()
        self.tf_state = deployment_state
        self.orm.undeployed = False
        self.orm.creation_step = None
        self.status = ClusterStatusCode.PROVISIONING_SUCCESS
        db.session.commit()

    def create_plan(self, github_sha=None, run_id=None):
        logger.debug(f"Call <{self.__class__.__name__}:create_plan>")

        self.tfcloud_run = TerraformCloudRunORM()

        try:
            if github_sha is None and run_id is None:
                raise InvalidPlanParameters

            tf = get_terraform_cloud()
            while run_id is None:
                run_id = tf.get_run_by_commit(self.tfcloud_workspace, github_sha)
                if run_id is None:
                    time.sleep(10)
            logger.debug(f"{github_sha=} match {run_id=}")

            self.orm.tfcloud_run.run_id = run_id
            db.session.commit()

            # A previous planned/pending runs can block the current run from running.
            # Force excecute the current run
            tf.force_execute(run_id)

            # Fetch lastest plan if currently empty
            while not self.plan:
                plan = tf.get_run_plan_log_json(run_id)
                if plan is not None:
                    self.plan = plan
                    logger.info(f"Plan Updated for {run_id=}")
                else:
                    logger.debug("wait for plan")
                    time.sleep(10)

            self.status = ClusterStatusCode.CREATED
        except Exception:
            db.session.rollback()
            self.status = ClusterStatusCode.PLAN_ERROR
            raise

    def complete_teardown(self):
        """Retain the definition and integrations after resources are removed."""
        self.orm.undeployed = True
        self.orm.applied_config = None
        self.orm.deployment_started_at = None
        self.orm.creation_step = None
        self.tfcloud_run = TerraformCloudRunORM()
        self.status = ClusterStatusCode.NOT_DEPLOYED
        db.session.commit()

    def validate_rebuild(self):
        # Refresh legacy initial plans before checking lifecycle eligibility.
        self.status
        if not self.orm.undeployed or not self.tfcloud_workspace:
            raise InvalidUsageException("Only an undeployed cluster with a workspace can be rebuilt")
        if self.expiration_date and datetime.date.fromisoformat(self.expiration_date) <= datetime.date.today():
            raise InvalidUsageException("Choose a future expiration date or no expiration before rebuilding")

    def plan_rebuild(self):
        self.validate_rebuild()
        # Writing the saved variables creates a fresh commit/run even when unchanged.
        sha = get_github_storage().write(self._get_var_tf(), self.hostname)
        self.create_plan(github_sha=sha)

    def destroy_empty_cluster(self):
        if self.is_busy:
            raise BusyClusterException
        tf = get_terraform_cloud()
        if self.tfcloud_workspace:
            tf.discard_workspace_plans(self.tfcloud_workspace)
            tf.lock_workspace(self.tfcloud_workspace)
            try:
                tf.verify_workspace_empty(self.tfcloud_workspace)
                self.delete(archive_repo=True)
            except Exception:
                tf.unlock_workspace(self.tfcloud_workspace)
                raise
        else:
            if self.tf_state is not None:
                raise InvalidUsageException("Cannot verify resources without the Terraform workspace")
            self.delete(archive_repo=True)

    def delete(self, archive_repo=False):
        if self.tfcloud_workspace:
            tf = get_terraform_cloud()
            tf.add_workspace_tag(self.tfcloud_workspace, "deleted")
        if archive_repo:
            get_github_storage().archive_repo(self.hostname)
        db.session.delete(self.orm)
        db.session.commit()

    def apply(self):
        if self.plan is None:
            raise PlanNotCreatedException
        if self.is_busy:
            raise BusyClusterException
        if self.tfcloud_run.run_id is None:
            raise RunIDNotSet

        tf = get_terraform_cloud()
        _, is_destroy = tf.get_run_status(self.tfcloud_run.run_id)
        if not is_destroy and self.orm.undeployed:
            self.validate_rebuild()
        if not is_destroy:
            self.orm.undeployed = False
            self.orm.deployment_started_at = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
            # Persist deployment intent before the remote apply can allocate resources.
            db.session.commit()
        tf.apply_run(self.tfcloud_run.run_id)
