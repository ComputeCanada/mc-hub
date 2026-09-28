<template>
  <div>
    <v-defaults-provider
      :defaults="{
        VTextField: { variant: 'underlined' },
        VSelect: { variant: 'underlined' },
        VCombobox: { variant: 'underlined' },
      }"
    >
      <v-form ref="form" v-model="validForm">
        <slot name="benchmark-fields" />
        <v-list-subheader>General configuration</v-list-subheader>
        <v-list class="pt-0">
          <div class="editor-row d-flex flex-wrap">
            <v-col cols="12" sm="6" class="py-0">
              <v-select
                v-if="!stateful && !specs.undeployed"
                v-model="localSpecs.cloud.id"
                item-value="id"
                item-title="name"
                :items="projects"
                label="Cloud project"
                @update:model-value="changeCloudProject"
              />
              <div v-else>
                <v-list-item-subtitle>Cloud project</v-list-item-subtitle>
                <v-list-item-title>{{ localSpecs.cloud.name }}</v-list-item-title>
              </div>
            </v-col>
            <v-col v-if="!benchmarkMode && !plannerMode && !specs.capacity_ends_at" cols="12" sm="6" class="py-0">
              <v-menu
                v-model="expirationMenu"
                :close-on-content-click="false"
                transition="scale-transition"
                min-width="auto"
              >
                <template v-slot:activator="{ props }">
                  <v-text-field
                    v-model="localSpecs.expiration_date"
                    label="Expiration date"
                    :rules="[expirationRule]"
                    clearable
                    prepend-icon="mdi-calendar"
                    readonly
                    v-bind="props"
                  ></v-text-field>
                </template>
                <v-date-picker v-model="expirationDate" :min="tomorrowDate"></v-date-picker>
              </v-menu>
            </v-col>
          </div>
          <div class="editor-row d-flex flex-wrap" v-if="!existingCluster">
            <v-col cols="12" sm="6" class="py-0">
              <v-text-field
                v-model="localSpecs.cluster_name"
                label="Cluster name"
                :readonly="identityLocked"
                :rules="[clusterNameRegexRule, benchmarkHostnameRule]"
                :persistent-hint="benchmarkMode"
                validate-on="blur"
              />
            </v-col>
            <v-col v-if="showDeploymentConfiguration" cols="12" sm="6" class="py-0">
              <v-select
                v-model="localSpecs.domain"
                :items="getPossibleValues('domain')"
                label="Domain"
                :readonly="identityLocked"
                :rules="[domainRule]"
              />
            </v-col>
          </div>
          <div class="editor-row d-flex flex-wrap" v-if="showDeploymentConfiguration">
            <v-col cols="12" sm="6" class="py-0">
              <v-select v-if="!stateful" v-model="localSpecs.image" :items="getPossibleValues('image')" label="Image" />
              <div v-else>
                <v-list-item-subtitle>Image</v-list-item-subtitle>
                <v-list-item-title>{{ localSpecs.image }}</v-list-item-title>
              </div>
            </v-col>
            <v-col cols="12" sm="6" class="py-0">
              <v-select
                v-if="!existingCluster || specs.undeployed"
                v-model="localSpecs.mc_version"
                :items="getPossibleValues('mc_version')"
                label="Magic Castle Version"
                :rules="[versionRule]"
              />
              <div v-else>
                <v-list-item-subtitle>Magic Castle Version</v-list-item-subtitle>
                <v-list-item-title>{{ localSpecs.mc_version }}</v-list-item-title>
              </div>
            </v-col>
          </div>
          <div class="editor-row d-flex flex-wrap" v-if="isAWS">
            <v-col cols="12" sm="6" class="py-0">
              <v-select
                v-model="localSpecs.availability_zone"
                :items="(possibleResources && possibleResources.availability_zone) || []"
                label="Availability zone (optional)"
                hint="Leave empty to use the deployment default and show only instance types offered in every available zone."
                persistent-hint
                clearable
              />
            </v-col>
          </div>
        </v-list>
        <v-divider />

        <!-- Instances -->
        <v-progress-linear v-if="loading" indeterminate aria-label="Loading cloud resources" />
        <v-alert v-if="resourceError" type="error"
          >{{ resourceError }} <v-btn variant="text" @click="loadCloudResources">Retry</v-btn></v-alert
        >
        <v-alert v-if="isAWS" :type="awsStatus === 'ready' ? 'success' : awsStatus === 'blocked' ? 'error' : 'info'">
          {{
            awsStatus === "ready"
              ? "Within quotas"
              : awsStatus === "blocked"
              ? "Cluster definition is blocked"
              : awsChecking
              ? "Checking cluster feasibility…"
              : "Unable to verify cluster feasibility"
          }}
          <div v-for="(issue, index) in awsFeasibility ? awsFeasibility.issues : []" :key="index">
            {{ issue.message }}
          </div>
          <div v-if="awsError">{{ awsError }} <v-btn variant="text" @click="checkAWS">Retry</v-btn></div>
        </v-alert>
        <v-list v-if="showOpenStackQuotas" class="pt-0">
          <div class="editor-row d-flex flex-wrap">
            <v-col cols="12" sm="3">
              <resource-usage-display :max="instanceCountMax" :used="instanceCountUsed" title="Instances" />
            </v-col>
            <v-col cols="12" sm="3">
              <resource-usage-display :max="ramGbMax" :used="ramGbUsed" title="RAM" suffix="GiB" />
            </v-col>
            <v-col cols="12" sm="3">
              <resource-usage-display :max="vcpuMax" :used="vcpuUsed" title="cores" />
            </v-col>
            <v-col cols="12" sm="3">
              <resource-usage-display :max="volumeCountMax" :used="volumeCountUsed" title="volumes" />
            </v-col>
          </div>
        </v-list>
        <v-list>
          <div :key="id" v-for="id in Object.keys(localSpecs.instances)">
            <div class="instance-row-scroll">
              <div class="instance-row">
                <v-col class="pt-0 instance-field">
                  <v-text-field
                    v-model.number="localSpecs.instances[id].count"
                    label="count"
                    min="0"
                    type="number"
                    :rules="[countRule]"
                  />
                </v-col>
                <v-col class="pt-0 instance-field">
                  <v-text-field
                    :model-value="id"
                    label="hostname prefix"
                    @change="changeHostnamePrefix(id, $event.target.value)"
                    :rules="[hostnamePrefixRule(id)]"
                  />
                </v-col>
                <v-col class="pt-0 instance-field">
                  <type-select
                    :types="getTypes(localSpecs.instances[id].tags, id)"
                    :loading="loading || (isAWS && !awsChoicesLoaded && awsChecking)"
                    v-model="localSpecs.instances[id].type"
                    label="Type"
                    :rules="isAWS ? [awsTypeRule(id)] : [ramRule, coreRule]"
                  />
                </v-col>
                <v-col class="pt-0 instance-field">
                  <v-combobox
                    v-model="localSpecs.instances[id].tags"
                    :items="TAGS"
                    label="tags"
                    :rules="[publicTagRule(id)]"
                    multiple
                  ></v-combobox>
                </v-col>
                <v-col class="pt-0 instance-field">
                  <span v-if="instanceSettingsErrors[id]" class="text-error text-caption d-block">Check settings</span>
                  <span v-else-if="optionalAttributeCount(id)" class="text-caption d-block"
                    >{{ optionalAttributeCount(id) }} set</span
                  >
                  <v-btn
                    icon
                    variant="text"
                    size="small"
                    :aria-label="`Optional settings for ${id}`"
                    :aria-expanded="expandedInstance === id ? 'true' : 'false'"
                    :aria-controls="`instance-settings-${id}`"
                    @click="expandedInstance = expandedInstance === id ? null : id"
                  >
                    <v-icon>{{ expandedInstance === id ? "mdi-chevron-up" : "mdi-chevron-down" }}</v-icon>
                  </v-btn>
                  <v-btn @click="rmInstanceRow(id)" class="ml-4" variant="text" icon size="small" color="error">
                    <v-icon> mdi-delete </v-icon>
                  </v-btn>
                </v-col>
              </div>
            </div>
            <v-expand-transition>
              <div v-show="expandedInstance === id" :id="`instance-settings-${id}`">
                <instance-settings
                  v-model:instance="localSpecs.instances[id]"
                  :name="id"
                  :provider="provider"
                  :has-gpu="instanceHasGpu(localSpecs.instances[id].type)"
                  :images="getPossibleValues('image')"
                  :additional-mig-profiles="getPossibleValues('additional_mig_profiles') || []"
                  @invalid="instanceSettingsErrors[id] = $event"
                />
              </div>
            </v-expand-transition>
          </div>
          <div class="text-center">
            <v-btn @click="addInstanceRow" color="primary" class="ma-2"> Add instance row </v-btn>
          </div>
        </v-list>
        <v-divider />
        <!-- Volumes -->
        <div class="volumes">
          <v-list v-if="showOpenStackQuotas">
            <div class="editor-row d-flex flex-wrap">
              <v-spacer></v-spacer>
              <v-col cols="12" sm="3">
                <resource-usage-display
                  :max="volumeSizeMax"
                  :used="volumeSizeUsed"
                  title="volume storage"
                  suffix="GB"
                />
              </v-col>
              <v-col cols="12" sm="3">
                <resource-usage-display :max="volumeCountMax" :used="volumeCountUsed" title="volumes" />
              </v-col>
              <v-spacer></v-spacer>
            </div>
          </v-list>
          <v-list>
            <div :key="tag" v-for="tag in Object.keys(localSpecs.volumes)">
              <div :key="id" v-for="id in Object.keys(localSpecs.volumes[tag])">
                <div class="editor-row d-flex flex-wrap">
                  <v-spacer></v-spacer>
                  <v-col cols="12" sm="2" class="pt-0">
                    <v-combobox
                      :items="Object.keys(localSpecs.volumes)"
                      :model-value="tag"
                      @update:model-value="changeVolumeTag(tag, id, $event)"
                      label="tag"
                      :readonly="stateful && id in (initialSpecs.volumes.nfs || {})"
                    ></v-combobox>
                    <!-- <v-text-field :model-value="tag" label="tag" readonly /> -->
                  </v-col>
                  <v-col cols="12" sm="3" class="pt-0">
                    <v-text-field
                      :model-value="id"
                      label="volume name"
                      @change="changeVolumeName(id, $event.target.value, tag)"
                      :rules="[volumeNameRule(id, tag)]"
                      :readonly="stateful && id in (initialSpecs.volumes.nfs || {})"
                    />
                  </v-col>
                  <v-col cols="12" sm="2" class="pt-0">
                    <v-text-field
                      v-model.number="localSpecs.volumes[tag][id].size"
                      type="number"
                      label="size"
                      prefix="GB"
                      :rules="
                        isAWS
                          ? [greaterThanZeroRule, awsVolumeSizeRule]
                          : [volumeCountRule, volumeSizeRule, greaterThanZeroRule]
                      "
                      min="0"
                      dir="rtl"
                      reverse
                      :readonly="stateful && id in (initialSpecs.volumes.nfs || {})"
                    />
                  </v-col>
                  <v-col cols="12" sm="1" class="pt-0">
                    <v-btn
                      @click="rmVolumeRow(id, tag)"
                      variant="text"
                      icon
                      size="small"
                      color="error"
                      :disabled="stateful && id in (initialSpecs.volumes.nfs || {})"
                    >
                      <v-icon> mdi-delete </v-icon>
                    </v-btn>
                  </v-col>
                  <v-spacer></v-spacer>
                </div>
              </div>
            </div>
            <div class="text-center">
              <v-btn @click="addVolumeRow" color="primary" class="ma-2"> Add volume row </v-btn>
            </div>
            <v-divider />
          </v-list>
        </div>

        <!-- Networking & security -->
        <v-list-subheader v-if="showDeploymentConfiguration && !benchmarkMode"
          >Networking and security</v-list-subheader
        >
        <v-list v-if="showDeploymentConfiguration">
          <template v-if="!benchmarkMode">
            <div class="editor-row d-flex flex-wrap">
              <v-combobox
                v-model="localSpecs.public_keys"
                label="SSH Keys"
                multiple
                chips
                clearable
                closable-chips
                :rules="[publicKeysRule]"
                hint="Paste a key then press enter. Only the comment section will be displayed."
              >
                <template #chip="{ item, props }">
                  <v-chip v-bind="props" closable close-icon="mdi-delete">
                    {{
                      item.raw.split(" ").length > 2
                        ? item.raw.split(" ")[2]
                        : item.raw.slice(0, 15) + "..." + item.raw.slice(-5)
                    }}
                  </v-chip>
                </template>
              </v-combobox>
            </div>
            <div class="editor-row d-flex flex-wrap">
              <v-text-field v-model.number="localSpecs.nb_users" type="number" label="Number of guest users" min="0" />
            </div>
            <div class="editor-row d-flex flex-wrap" v-if="!stateful">
              <v-text-field v-model="localSpecs.guest_passwd" label="Guest password" :rules="[passwordLengthRule]" />
              <v-tooltip location="bottom">
                <template #activator="{ props }">
                  <v-btn icon variant="text" v-bind="props" @click="generateGuestPassword()">
                    <v-icon>mdi-refresh</v-icon>
                  </v-btn>
                </template>
                <span>Generate new password</span>
              </v-tooltip>
            </div>
            <div class="editor-row d-flex flex-wrap" v-else>
              <div>
                <v-list-item-subtitle>Guest password</v-list-item-subtitle>
                <v-list-item-title>{{ localSpecs.guest_passwd }}</v-list-item-title>
              </div>
            </div>
          </template>
          <v-list-group prepend-icon="mdi-script-text-outline">
            <template #activator="{ props }">
              <v-list-item v-bind="props" title="Additional puppet configuration (optional)" />
            </template>
            <div class="editor-row d-flex flex-wrap">
              <div>
                <span class="mb-4" style="line-height: 18pt"
                  >Configuration variables are documented in
                  <a
                    href="https://github.com/ComputeCanada/puppet-magic_castle/blob/master/README.md#puppet-magic-castle"
                    target="_blank"
                    >puppet-magic_castle</a
                  >
                  and
                  <a
                    href="https://github.com/ComputeCanada/puppet-jupyterhub/blob/master/README.md#hieradata-configuration"
                    target="_blank"
                    >puppet-jupyterhub</a
                  >.
                </span>

                <hieradata-editor v-model="localSpecs.hieradata_entries" />
              </div>
            </div>
          </v-list-group>
        </v-list>

        <!-- Apply and cancel -->
        <div class="text-center">
          <p v-if="!validForm" class="text-error">Some form fields are invalid.</p>
          <v-btn
            @click="apply"
            color="primary"
            class="ma-2"
            :disabled="!applyButtonEnabled || submitDisabled || validating"
            size="large"
            >{{ submitLabel || (specs.undeployed ? "Save configuration" : "Apply") }}</v-btn
          >
          <v-btn
            v-if="specs.undeployed"
            color="primary"
            class="ma-2"
            :disabled="loading || validating || dirtyForm || validForm === false || (isAWS && awsStatus !== 'ready')"
            size="large"
            @click="apply('rebuild')"
            >{{ status === "created" ? "Review build plan" : "Rebuild" }}</v-btn
          >
          <p v-if="specs.undeployed">
            Save any configuration changes before rebuilding. Choose a future expiration date or no expiration.
            Rebuilding creates new resources; deleted data is not restored and connection details may change.
          </p>
          <v-btn
            :to="plannerMode ? undefined : benchmarkMode ? '/benchmarks' : '/'"
            @click="plannerMode && $emit('cancel')"
            class="ma-2"
            :disabled="loading"
            size="large"
            variant="outlined"
            color="primary"
            >Cancel</v-btn
          >
        </div>
      </v-form>
    </v-defaults-provider>
  </div>
</template>

<script>
import cloneDeep from "lodash/cloneDeep";
import isEqual from "lodash/isEqual";
import { isGpuTypeName } from "@/models/instanceTypes";
import { generatePassword, generatePetName } from "@/models/utils";
import ClusterStatusCode from "@/models/ClusterStatusCode";
import ResourceUsageDisplay from "@/components/ui/ResourceUsageDisplay";
import TypeSelect from "./TypeSelect";
import InstanceSettings from "./InstanceSettings";
import { VDefaultsProvider } from "vuetify/components/VDefaultsProvider";
import HieradataEditor from "@/components/ui/HieradataEditor";
import AvailableResourcesRepository from "@/repositories/AvailableResourcesRepository";
import ProjectRepository from "@/repositories/ProjectRepository";
import UserRepository from "@/repositories/UserRepository";

const MB_PER_GB = 1024;
const MINIMUM_PASSWORD_LENGTH = 8;
const CLUSTER_NAME_REGEX = /^[a-z]([a-z0-9-]*[a-z0-9]+)?$/;
const SSH_PUBLIC_KEY_REGEX =
  /^(ssh-rsa AAAAB3NzaC1yc2|ecdsa-sha2-nistp256 AAAAE2VjZHNhLXNoYTItbmlzdHAyNT|ecdsa-sha2-nistp384 AAAAE2VjZHNhLXNoYTItbmlzdHAzODQAAAAIbmlzdHAzOD|ecdsa-sha2-nistp521 AAAAE2VjZHNhLXNoYTItbmlzdHA1MjEAAAAIbmlzdHA1Mj|ssh-ed25519 AAAAC3NzaC1lZDI1NTE5|ssh-dss AAAAB3NzaC1kc3)[0-9A-Za-z+/]+[=]{0,3}( .*)?$/;

export default {
  name: "ClusterEditor",
  emits: ["input", "apply", "rebuild", "cancel", "loading"],
  components: {
    HieradataEditor,
    VDefaultsProvider,
    TypeSelect,
    InstanceSettings,
    ResourceUsageDisplay,
  },
  props: {
    benchmarkMode: Boolean,
    plannerMode: Boolean,
    autoCreate: Boolean,
    identityLocked: Boolean,
    preserveSpecs: Boolean,
    submitDisabled: Boolean,
    submitLabel: String,
    projectIds: Array,
    specs: {
      type: Object,
      required: true,
    },
    existingCluster: {
      type: Boolean,
      required: true,
    },
    status: {
      type: String,
    },
    stateful: {
      type: Boolean,
    },
  },
  data: function () {
    return {
      DEFAULT_VOLUMES: ["home", "project", "scratch"],
      VOLUME_STUB: { size: 50 },
      TAGS: ["mgmt", "puppet", "nfs", "login", "proxy", "public", "node", "pool", "dtn"],
      expandedInstance: null,
      instanceSettingsErrors: {},
      validForm: null,
      validating: false,
      expirationMenu: false,
      initialSpecs: null,

      clusterNameRegexRule: (value) =>
        (value || "").match(CLUSTER_NAME_REGEX) !== null ||
        "Must contain lowercase alphanumeric characters and start with a letter. It can also include dashes.",
      awsVolumeSizeRule: (value) => Number.isInteger(Number(value)) || "Use a whole number of GiB",
      greaterThanZeroRule: (value) =>
        (value !== "" && value != null && Number(value) > 0) || "Must be greater than zero",
      positiveNumberRule: (value) =>
        (value !== "" && value != null && Number(value) >= 0) || "Must be a positive number",
      passwordLengthRule: (value) =>
        (value || "").length >= MINIMUM_PASSWORD_LENGTH ||
        `The password must be at least ${MINIMUM_PASSWORD_LENGTH} characters long`,
      nowDate: new Date().toISOString().slice(0, 10),
      tomorrowDate: new Date(new Date().getTime() + 24 * 60 * 60 * 1000).toISOString().slice(0, 10),
      promise: null,
      quotas: null,
      provider: null,
      resourceError: "",
      resourceRequest: 0,
      awsFeasibility: null,
      awsChoices: {},
      awsChoicesLoaded: false,
      awsChecking: false,
      awsError: "",
      awsTimer: null,
      awsRequest: 0,
      awsInFlight: false,
      awsCheckedDefinition: null,
      awsDisposed: false,
      possibleResources: null,
      resourceDetails: null,
      projects: [],
    };
  },
  watch: {
    awsDefinition: {
      deep: true,
      handler() {
        this.scheduleAWS();
      },
    },
    specs(value) {
      this.initialSpecs = cloneDeep(value);
    },
    promise() {
      this.$emit("loading", this.loading);
    },
    possibleResources(possibleResources) {
      if (possibleResources === null) return;
      // We set default values for select boxes based on possible resources fetched from the API
      // Domain
      if (this.localSpecs.domain === null) {
        try {
          this.localSpecs.domain = possibleResources.domain[0];
          this.initialSpecs.domain = possibleResources.domain[0];
        } catch (err) {
          // Leave the selection unset when resource discovery has no domain.
        }
      }

      // Image
      if (this.localSpecs.image === null) {
        try {
          this.localSpecs.image = possibleResources.image[0];
          this.initialSpecs.image = possibleResources.image[0];
        } catch (err) {
          // Leave the selection unset when resource discovery has no image.
        }
      }

      // Magic Castle version
      if (this.localSpecs.mc_version === null) {
        try {
          this.localSpecs.mc_version = possibleResources.mc_version[0];
          this.initialSpecs.mc_version = possibleResources.mc_version[0];
        } catch (err) {
          // Leave the selection unset when resource discovery has no version.
        }
      }

      if (this.isAWS) return;

      // Instance type
      for (let key in this.localSpecs.instances) {
        if (this.localSpecs.instances[key].type === null) {
          try {
            const type = this.getTypes(this.localSpecs.instances[key].tags)[0];
            this.localSpecs.instances[key].type = type?.name;
            if (key in this.initialSpecs.instances) {
              this.initialSpecs.instances[key].type = type?.name;
            }
          } catch (err) {
            // Leave the selection unset when no compatible type is available.
          }
        }
      }
    },
    dirtyForm(dirty) {
      if (dirty && this.stateful) {
        this.$enableUnloadConfirmation();
      } else {
        this.$disableUnloadConfirmation();
      }
    },
  },
  created() {
    // Declare the optional field before taking the baseline for dirty-form checks.
    if (!("availability_zone" in this.localSpecs)) this.localSpecs.availability_zone = null;
    if (!this.existingCluster && !this.preserveSpecs) {
      this.localSpecs.cluster_name = generatePetName();
      this.localSpecs.guest_passwd = generatePassword();
    }
    if (!this.stateful) {
      const user_promise = UserRepository.getCurrent();
      const project_promise = ProjectRepository.getAll();
      this.promise = Promise.all([user_promise, project_promise]);
      this.promise
        .then((values) => {
          if (this.awsDisposed) return;
          const user = values[0].data;
          const projects = values[1].data;
          this.projects = this.projectIds ? projects.filter((p) => this.projectIds.includes(p.id)) : projects;
          if (!this.existingCluster && !this.preserveSpecs) {
            const project = this.projects.find((project) => project.id === user.default_project_id) || this.projects[0];
            this.localSpecs.cloud.id = project?.id;
            this.localSpecs.cloud.name = project?.name;
            this.localSpecs.public_keys = user.public_keys.filter((key) => key.match(SSH_PUBLIC_KEY_REGEX));
          }
          this.initialSpecs = cloneDeep(this.localSpecs);
          this.loadCloudResources();
        })
        .catch((error) => {
          if (this.awsDisposed) return;
          this.resourceError = error.response?.data?.message || "Unable to load project settings. Reload to retry.";
          this.promise = null;
        });
    } else {
      this.initialSpecs = cloneDeep(this.localSpecs);
      this.loadCloudResources();
    }
  },
  beforeUnmount() {
    this.awsDisposed = true;
    clearTimeout(this.awsTimer);
    this.awsRequest++;
    this.resourceRequest++;
    this.$disableUnloadConfirmation();
  },
  computed: {
    expirationDate: {
      get() {
        return this.localSpecs.expiration_date ? new Date(`${this.localSpecs.expiration_date}T00:00:00`) : null;
      },
      set(value) {
        this.localSpecs.expiration_date = value
          ? `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}-${String(value.getDate()).padStart(
              2,
              "0"
            )}`
          : null;
        this.expirationMenu = false;
      },
    },
    showDeploymentConfiguration() {
      return !this.plannerMode || this.autoCreate;
    },
    benchmarkHostnameRule() {
      return (
        !this.benchmarkMode ||
        `${this.localSpecs.cluster_name}.int.${this.localSpecs.domain}`.length <= 63 ||
        "Cluster name + .int. + domain must be at most 63 characters."
      );
    },
    isAWS() {
      return this.provider === "aws";
    },
    showOpenStackQuotas() {
      return this.provider === "openstack" && this.quotas !== null && !this.loading;
    },
    awsStatus() {
      return this.awsChecking ? "checking" : this.awsFeasibility?.status;
    },
    awsDefinition() {
      return {
        cloud: this.localSpecs.cloud,
        instances: this.localSpecs.instances,
        image: this.localSpecs.image,
        availability_zone: this.localSpecs.availability_zone,
        volumes: this.localSpecs.volumes,
      };
    },
    loading() {
      return this.promise !== null;
    },
    localSpecs: {
      get() {
        return this.specs;
      },
      set(localSpecs) {
        this.$emit("input", localSpecs);
      },
    },
    hostname() {
      return this.localSpecs.cluster_name + "." + this.localSpecs.domain;
    },
    dirtyForm() {
      const keysToCheck = [
        "volumes",
        "nb_users",
        "domain",
        "cluster_name",
        "hieradata_entries",
        "image",
        "availability_zone",
        "mc_version",
        "public_keys",
        "guest_passwd",
        "instances",
        "expiration_date",
        "cloud",
      ];
      if (this.existingCluster) {
        if (this.initialSpecs === null) {
          return false;
        }
        if (
          [
            ClusterStatusCode.CREATED,
            ClusterStatusCode.PLAN_ERROR,
            ClusterStatusCode.BUILD_ERROR,
            ClusterStatusCode.PROVISIONING_ERROR,
            ClusterStatusCode.DESTROY_ERROR,
          ].includes(this.status) &&
          !this.specs.undeployed
        ) {
          return true;
        }
        return keysToCheck.some((key) => !isEqual(this.initialSpecs[key], this.localSpecs[key]));
      }
      return true;
    },
    domainRule() {
      return (
        (this.possibleResources && this.possibleResources.domain.includes(this.localSpecs.domain)) ||
        "Invalid domain provided"
      );
    },
    versionRule() {
      return (
        (this.possibleResources && this.possibleResources.mc_version.includes(this.localSpecs.mc_version)) ||
        "Invalid Magic Castle version provided"
      );
    },
    volumeCountRule() {
      return this.plannerMode || this.volumeCountUsed <= this.volumeCountMax || "Volume number quota exceeded";
    },
    volumeSizeRule() {
      return this.plannerMode || this.volumeSizeUsed <= this.volumeSizeMax || "Volume size quota exceeded";
    },
    instanceCountUsed() {
      return this.usedResourcesLoaded ? this.instances.reduce((acc, instance) => acc + instance.count, 0) : 0;
    },
    instanceCountMax() {
      return this.quotas?.instance_count?.max ?? 0;
    },
    ipsCountMax() {
      return this.quotas?.ips?.max ?? 0;
    },
    ramRule() {
      return this.plannerMode || this.ramGbUsed <= this.ramGbMax || "Ram quota exceeded";
    },
    coreRule() {
      return this.plannerMode || this.vcpuUsed <= this.vcpuMax || "Core quota exceeded";
    },
    ramGbUsed() {
      return this.usedResourcesLoaded
        ? this.instances.reduce(
            (acc, instance) => acc + instance.count * this.getInstanceDetail(instance.type, "ram"),
            0
          ) / MB_PER_GB
        : 0;
    },
    ramGbMax() {
      return (this.quotas?.ram?.max ?? 0) / MB_PER_GB;
    },
    vcpuUsed() {
      return this.usedResourcesLoaded
        ? this.instances.reduce(
            (acc, instance) => acc + instance.count * this.getInstanceDetail(instance.type, "vcpus"),
            0
          )
        : 0;
    },
    vcpuMax() {
      return this.quotas?.vcpus?.max ?? 0;
    },
    volumeCountUsed() {
      return this.usedResourcesLoaded
        ? this.instances.reduce(
            (acc, instance) => acc + instance.count * this.getInstanceDetail(instance.type, "required_volume_count"),
            0
          ) + Object.keys(this.localSpecs.volumes["nfs"]).length
        : 0;
    },
    volumeCountMax() {
      return this.quotas?.volume_count?.max ?? 0;
    },
    volumeSizeUsed() {
      return this.usedResourcesLoaded
        ? this.instancesVolumeSizeUsed +
            Object.values(this.localSpecs.volumes.nfs).reduce((acc, volume) => acc + volume.size, 0)
        : 0;
    },
    volumeSizeMax() {
      return this.quotas?.volume_size?.max ?? 0;
    },
    instancesVolumeSizeUsed() {
      return this.instances.reduce(
        (acc, instance) => acc + instance.count * this.getInstanceDetail(instance.type, "required_volume_size"),
        0
      );
    },
    instances() {
      return this.localSpecs ? Object.values(this.localSpecs.instances) : [];
    },
    usedResourcesLoaded() {
      return this.localSpecs !== null && this.resourceDetails !== null;
    },
    applyButtonEnabled() {
      return (
        !this.loading &&
        this.validForm !== false &&
        !Object.values(this.instanceSettingsErrors).some(Boolean) &&
        (this.plannerMode || this.benchmarkMode || (!this.existingCluster && this.preserveSpecs) || this.dirtyForm) &&
        !this.resourceError &&
        (this.plannerMode || !this.isAWS || this.awsStatus === "ready")
      );
    },
  },
  methods: {
    expirationRule(value) {
      return !value || value >= this.tomorrowDate || "Choose a future expiration date or no expiration.";
    },
    changeVolumeTag(oldTag, id, tag) {
      if (!tag || !/^[a-z][a-z0-9-]*$/.test(tag) || tag === oldTag) return;
      const target = Object.prototype.hasOwnProperty.call(this.localSpecs.volumes, tag)
        ? this.localSpecs.volumes[tag]
        : {};
      if (Object.prototype.hasOwnProperty.call(target, id)) return;
      this.localSpecs.volumes = {
        ...this.localSpecs.volumes,
        [tag]: { ...target, [id]: this.localSpecs.volumes[oldTag][id] },
      };
      delete this.localSpecs.volumes[oldTag][id];
    },
    scheduleAWS() {
      if (this.awsDisposed) return;
      if (this.awsFeasibility && !this.awsChecking && JSON.stringify(this.awsDefinition) === this.awsCheckedDefinition)
        return;
      clearTimeout(this.awsTimer);
      this.awsRequest++;
      this.awsFeasibility = null;
      if (!this.isAWS) return;
      this.awsChecking = true;
      this.awsTimer = setTimeout(() => this.checkAWS(), 350);
    },
    async checkAWS() {
      clearTimeout(this.awsTimer);
      if (!this.isAWS || this.awsInFlight || this.awsDisposed) return;
      this.awsInFlight = true;
      const requestId = ++this.awsRequest;
      this.awsChecking = true;
      this.awsError = "";
      try {
        const response = this.existingCluster
          ? await AvailableResourcesRepository.checkHost(this.hostname, this.awsDefinition)
          : await AvailableResourcesRepository.checkCloud(this.localSpecs.cloud.id, this.awsDefinition);
        if (requestId !== this.awsRequest) return;
        this.awsFeasibility = response.data.feasibility;
        this.awsChoices = response.data.instance_choices;
        this.awsChoicesLoaded = true;
        for (const [id, type] of Object.entries(response.data.instance_defaults || {})) {
          const group = this.localSpecs.instances[id];
          if (group && !group.type) group.type = type;
        }
        // These defaults were already checked together by the server.
        this.awsCheckedDefinition = JSON.stringify(this.awsDefinition);
      } catch (error) {
        if (requestId === this.awsRequest) {
          this.awsFeasibility = null;
          this.awsError = error.response?.data?.message || "AWS could not verify this definition. Retry.";
        }
      } finally {
        this.awsInFlight = false;
        if (requestId === this.awsRequest) this.awsChecking = false;
        else if (this.isAWS && !this.awsDisposed) {
          clearTimeout(this.awsTimer);
          this.awsTimer = setTimeout(() => this.checkAWS(), 350);
        }
      }
    },
    awsTypeRule(id) {
      return (value) =>
        (this.plannerMode && !!value) ||
        this.awsChoices[id]?.includes(value) ||
        "This type is unavailable for the current definition. Adjust the count or select another type.";
    },
    optionalAttributeCount(id) {
      return Object.keys(this.localSpecs.instances[id]).filter((key) => !["type", "count", "tags"].includes(key))
        .length;
    },
    changeHostnamePrefix(oldKey, newKey) {
      if (this.hostnamePrefixRule(oldKey)(newKey) === true && newKey !== oldKey) {
        const instances = this.localSpecs.instances;
        const new_instances = {};
        for (const key of Object.keys(instances)) {
          if (key == oldKey) {
            new_instances[newKey] = instances[oldKey];
          } else {
            new_instances[key] = instances[key];
          }
        }
        this.localSpecs.instances = new_instances;
        delete this.instanceSettingsErrors[oldKey];
        if (this.expandedInstance === oldKey) this.expandedInstance = newKey;
      }
    },
    changeVolumeName(oldKey, newKey, tag = "nfs") {
      if (this.volumeNameRule(oldKey, tag)(newKey) === true && newKey !== oldKey) {
        const nfs_volumes = this.localSpecs.volumes[tag];
        const new_nfs_volumes = {};
        for (const key of Object.keys(nfs_volumes)) {
          if (key == oldKey) {
            new_nfs_volumes[newKey] = nfs_volumes[oldKey];
          } else {
            new_nfs_volumes[key] = nfs_volumes[key];
          }
        }
        this.localSpecs.volumes[tag] = new_nfs_volumes;
      }
    },
    publicTagRule(id) {
      var self = this;
      return function (tags) {
        if (self.isAWS || self.plannerMode) return true;
        if (self.localSpecs.instances[id].count > 0 && tags.includes("public")) {
          let newPublicIP = 0;
          for (let key in self.localSpecs.instances) {
            if (self.localSpecs.instances[key].tags.includes("public")) {
              newPublicIP += self.localSpecs.instances[key].count;
            }
          }
          if (self.initialSpecs) {
            for (let key in self.initialSpecs.instances) {
              if (self.initialSpecs.instances[key].tags.includes("public")) {
                newPublicIP -= self.initialSpecs.instances[key].count;
              }
            }
          }
          return newPublicIP <= self.ipsCountMax || "Public IP quota exceeded";
        }
        return true;
      };
    },
    getTypes(tags, id) {
      if (this.possibleResources === null || this.resourceDetails === null) {
        return [];
      }
      if (this.isAWS && !this.plannerMode) {
        const allowed = new Set(this.awsChoices[id] || []);
        const selected = this.localSpecs.instances[id]?.type;
        return this.resourceDetails.instance_types
          .filter((t) => allowed.has(t.name) || t.name === selected)
          .map((t) => ({ ...t, unavailable: !allowed.has(t.name) }));
      }
      if (this.isAWS && this.plannerMode) return this.resourceDetails.instance_types;
      // Retrieve all available types
      // Then filter based on the selected tags
      let allowedNames = this.possibleResources["types"];
      for (const tag of tags) {
        if (tag in this.possibleResources["tag_types"]) {
          const tag_types = new Set(this.possibleResources["tag_types"][tag]);
          allowedNames = allowedNames.filter((x) => tag_types.has(x));
        }
      }
      const allowedNamesSet = new Set(allowedNames);
      return this.resourceDetails.instance_types.filter((t) => allowedNamesSet.has(t.name));
    },
    getPossibleValues(fieldPath) {
      if (this.isAWS && fieldPath === "image" && this.resourceDetails) {
        return (this.resourceDetails.images || []).map((image) => ({
          title: `${image.name} (${image.id})`,
          value: image.id,
        }));
      }
      if (this.possibleResources === null) {
        return [];
      } else {
        return fieldPath.split(".").reduce((acc, x) => acc[x], this.possibleResources);
      }
    },
    instanceHasGpu(instanceType) {
      // Match TypeSelect's GPU category even when API GPU metadata is missing or empty.
      if (isGpuTypeName(instanceType)) return true;
      const type = this.resourceDetails?.instance_types?.find((item) => item.name === instanceType);
      if (!type) return false;
      if (Array.isArray(type.gpus)) return type.gpus.some((gpu) => gpu.count == null || gpu.count > 0);
      if (typeof type.gpus === "number") return type.gpus > 0;
      return false;
    },
    getInstanceDetail(instanceType, detailName, defaultValue = 0) {
      const matchingInstances = this.resourceDetails.instance_types.filter(
        (instanceTypeDetails) => instanceTypeDetails.name === instanceType
      );
      if (matchingInstances.length > 0) {
        return matchingInstances[0][detailName];
      } else {
        return defaultValue;
      }
    },
    countRule(value) {
      return value !== "" || "cannot be empty";
    },
    hostnamePrefixRule(id) {
      var self = this;
      return function (value) {
        if (value == "") {
          return "cannot be empty";
        }
        if (value != id && value in self.localSpecs.instances) {
          return "must be unique";
        }
        if (!/^[a-z][a-z0-9-]*$/.test(value)) {
          return "must match [a-z][-a-z0-9]*";
        }
        return true;
      };
    },
    volumeNameRule(id, tag = "nfs") {
      var self = this;
      return function (value) {
        if (value == "") {
          return "cannot be empty";
        }
        if (value != id && value in self.localSpecs.volumes[tag]) {
          return "must be unique";
        }
        if (!/^[a-z][a-z0-9-]*$/.test(value)) {
          return "must match [a-z][-a-z0-9]*";
        }
        return true;
      };
    },
    publicKeysRule(values) {
      if (values instanceof Array && values.length == 0) {
        return "Required - Paste a key then press enter. Only the comment section will be displayed.";
      }
      return (
        this.localSpecs.public_keys.every((publicKey) => publicKey.match(SSH_PUBLIC_KEY_REGEX) !== null) ||
        "Invalid SSH public key"
      );
    },
    rmInstanceRow(id) {
      delete this.localSpecs.instances[id];
      delete this.instanceSettingsErrors[id];
      if (this.expandedInstance === id) this.expandedInstance = null;
    },
    addInstanceRow() {
      const alphabet = "abcdefghijklmnopqrstuvwxyz";
      const keys = Object.keys(this.localSpecs.instances);
      const all_tags = new Set(Array.prototype.concat(...keys.map((x) => this.localSpecs.instances[x].tags)));
      let new_row_key;
      const stub = { count: 0, type: null, tags: [] };

      // All tags are filled, move on to copying the last row
      if (!all_tags.has("mgmt")) {
        new_row_key = "mgmt";
        stub["count"] = 1;
        stub["tags"] = ["mgmt", "puppet", "nfs"];
        stub["type"] = this.getTypes(stub["tags"])[0]?.name;
      } else if (!all_tags.has("login")) {
        new_row_key = "login";
        stub["count"] = 1;
        stub["tags"] = ["login", "proxy", "public"];
        stub["type"] = this.getTypes(stub["tags"])[0]?.name;
      } else if (!all_tags.has("node")) {
        new_row_key = "node";
        stub["count"] = 1;
        stub["tags"] = ["node"];
        stub["type"] = this.getTypes(stub["tags"])[0]?.name;
      } else {
        const key = keys[keys.length - 1];
        let prefix;
        let suffix;
        if (key.indexOf("-") != -1) {
          const prefix_split = key.split("-", 2);
          prefix = prefix_split[0];
          suffix = alphabet[(alphabet.indexOf(prefix_split[1]) + 1) % 26];
        } else {
          prefix = key;
          suffix = "a";
        }
        const stub_tags = this.localSpecs.instances[key].tags;
        const stub_type = this.localSpecs.instances[key].type;
        stub["count"] = 1;
        stub["type"] = stub_type;
        stub["tags"] = stub_tags;
        new_row_key = `${prefix}-${suffix}`;
      }
      this.localSpecs.instances[new_row_key] = stub;
    },
    addVolumeRow() {
      const nfs_volumes = new Set(Object.keys(this.localSpecs.volumes["nfs"]));
      let key = null;
      for (const vol of this.DEFAULT_VOLUMES) {
        if (!nfs_volumes.has(vol)) {
          key = vol;
          break;
        }
      }
      if (key === null) {
        const vol_array = Object.keys(this.localSpecs.volumes["nfs"]).filter((value) =>
          /^volume[0-9]{1,}$/.test(value)
        );
        if (vol_array.length > 0) {
          const index = Math.max(...vol_array.map((value) => Number(value.replace(/^volume/, "")))) + 1;
          key = `volume${index}`;
        } else {
          key = `volume1`;
        }
      }
      const stub = Object.assign({}, this.VOLUME_STUB);
      this.localSpecs.volumes["nfs"][key] = stub;
    },
    rmVolumeRow(id, tag = "nfs") {
      delete this.localSpecs.volumes[tag][id];
    },
    async apply(action) {
      const rebuild = action === "rebuild";
      if (this.validating || this.submitDisabled || this.loading) return;
      this.validating = true;
      try {
        const { valid } = await this.$refs.form.validate();
        const enabled = rebuild
          ? !this.loading && !this.dirtyForm && !this.resourceError && (!this.isAWS || this.awsStatus === "ready")
          : this.applyButtonEnabled;
        if (valid && !this.awsDisposed && enabled && !this.submitDisabled) this.$emit(rebuild ? "rebuild" : "apply");
      } finally {
        this.validating = false;
      }
    },
    generateGuestPassword() {
      this.localSpecs.guest_passwd = generatePassword();
    },
    changeCloudProject() {
      const project = this.projects.find((project) => project.id === this.localSpecs.cloud.id);
      this.localSpecs.cloud.name = project?.name;
      this.quotas = null;
      this.localSpecs.availability_zone = null;
      for (let key in this.localSpecs.instances) {
        this.localSpecs.instances[key].type = null;
      }
      this.localSpecs.image = null;
      this.loadCloudResources();
    },

    async loadCloudResources() {
      if (this.awsDisposed) return;
      if (this.localSpecs.cloud.id == null) {
        this.promise = null;
        return;
      }
      const requestId = ++this.resourceRequest;
      this.awsRequest++;
      clearTimeout(this.awsTimer);
      this.provider = null;
      this.possibleResources = null;
      this.resourceDetails = null;
      this.quotas = null;
      this.awsChecking = false;
      this.awsError = "";
      this.awsFeasibility = null;
      this.awsCheckedDefinition = null;
      this.awsChoices = {};
      this.awsChoicesLoaded = false;
      this.resourceError = "";
      const request = this.existingCluster
        ? AvailableResourcesRepository.getHost(this.hostname)
        : AvailableResourcesRepository.getCloud(this.localSpecs.cloud.id);
      // The exposed loading promise settles even when the request fails; the
      // editor owns error presentation and callers may await loading completion.
      this.promise = request.then(
        (response) => ({ response }),
        (error) => ({ error })
      );
      try {
        const result = await this.promise;
        if (result.error) throw result.error;
        const { data } = result.response;
        if (requestId !== this.resourceRequest) return;
        this.provider = data.provider || "openstack";
        if (!this.localSpecs.volumes.nfs) this.localSpecs.volumes.nfs = {};
        this.resourceDetails = data.resource_details;
        const quotas = (this.plannerMode || this.benchmarkMode) && data.total_quotas ? data.total_quotas : data.quotas;
        this.quotas = this.isAWS
          ? null
          : Object.fromEntries(
              Object.entries(quotas || {}).map(([key, quota]) => [
                key,
                { ...quota, max: quota.max === null ? Infinity : quota.max },
              ])
            );
        this.possibleResources = data.possible_resources;
        this.scheduleAWS();
      } catch (error) {
        if (requestId === this.resourceRequest)
          this.resourceError = error.response?.data?.message || "Unable to load cloud resources. Retry.";
      } finally {
        if (requestId === this.resourceRequest) this.promise = null;
      }
    },
  },
};
</script>

<style scoped>
.instance-row-scroll {
  container-type: inline-size;
}
.instance-row {
  display: grid;
  grid-template-columns: 104px 152px minmax(160px, 1fr) minmax(176px, 1.2fr) 104px;
  align-items: center;
}
.instance-row > .instance-field {
  min-width: 0;
  padding-left: 4px;
  padding-right: 4px;
}
@container (max-width: 700px) {
  .instance-row {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@container (max-width: 360px) {
  .instance-row {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
