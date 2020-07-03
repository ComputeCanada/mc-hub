<template>
  <div>
    <v-container>
      <v-card max-width="600" class="mx-auto" :loading="loading">
        <template #progress>
          <v-progress-linear :indeterminate="progress === 0" :value="progress" />
        </template>
        <v-card-title v-if="existingCluster" class="mx-auto pl-8">Magic Castle Modification</v-card-title>
        <v-card-title v-else class="mx-auto pl-8">Magic Castle Creation</v-card-title>
        <v-card-text>
          <v-form v-model="validForm">
            <v-subheader>General configuration</v-subheader>
            <v-list class="pb-0">
              <v-list-item>
                <div style="display: flex; align-items: center; width: 100%">
                  <v-text-field
                    v-if="existingCluster"
                    v-model="clusterName"
                    label="Cluster name"
                    disabled
                  />
                  <v-text-field
                    v-else
                    v-model="magicCastle.cluster_name"
                    label="Cluster name"
                    :rules="[clusterNameRegexRule]"
                  />
                  <status-chip class="ml-3" :status="currentStatus" />
                </div>
              </v-list-item>
            </v-list>
            <template v-if="magicCastle !== null">
              <v-list class="pt-0">
                <v-list-item>
                  <v-text-field
                    v-model="magicCastle.domain"
                    label="Domain"
                    :disabled="existingCluster"
                  />
                </v-list-item>
                <v-list-item>
                  <v-select
                    v-model="magicCastle.image"
                    :items="getPossibleValues('image')"
                    label="Image"
                  />
                </v-list-item>
                <v-list-item>
                  <v-text-field
                    v-model.number="magicCastle.nb_users"
                    type="number"
                    label="Number of users"
                    :rules="[positiveNumberRule]"
                  />
                </v-list-item>
              </v-list>
              <v-divider />

              <!-- Instances -->
              <v-subheader>Node instances</v-subheader>
              <v-list>
                <div :key="id" v-for="[id, label] in Object.entries(NODE_LABELS)">
                  <v-list-item>
                    <v-col cols="12" sm="3" class="pl-0">
                      <p>{{ label }}</p>
                    </v-col>

                    <v-col cols="12" sm="5">
                      <v-select
                        :items="getPossibleValues(`instances.${id}.type`)"
                        v-model="magicCastle.instances[id].type"
                        label="Type"
                        :rules="instanceRules"
                      />
                    </v-col>

                    <v-col cols="12" sm="4">
                      <v-text-field
                        v-model.number="magicCastle.instances[id].count"
                        type="number"
                        label="Count"
                        :rules="[greaterThanZeroRule, ...instanceRules]"
                      />
                    </v-col>
                  </v-list-item>
                  <v-divider />
                </div>
                <v-list-item>
                  <v-col cols="12" sm="4">
                    <resource-usage-display
                      :max="instanceCountMax"
                      :used="instanceCountUsed"
                      title="Instances"
                    />
                  </v-col>
                  <v-col cols="12" sm="4">
                    <resource-usage-display
                      :max="ramGbMax"
                      :used="ramGbUsed"
                      title="RAM"
                      suffix="GB"
                    />
                  </v-col>
                  <v-col cols="12" sm="4">
                    <resource-usage-display :max="vcpuMax" :used="vcpuUsed" title="cores" />
                  </v-col>
                </v-list-item>
                <v-divider />
              </v-list>

              <!-- Storage -->
              <v-subheader>Storage</v-subheader>
              <v-list>
                <v-list-item>
                  <v-col cols="12" sm="3" class="pl-0">Type</v-col>
                  <v-col cols="12" sm="9">
                    <v-select
                      :items="getPossibleValues('storage.type')"
                      v-model="magicCastle.storage.type"
                    />
                  </v-col>
                </v-list-item>
                <v-divider />
                <div :key="id" v-for="[id, label] in Object.entries(STORAGE_LABELS)">
                  <v-list-item>
                    <v-col cols="12" sm="3" class="pl-0">{{ label }} size</v-col>
                    <v-col cols="12" sm="9">
                      <v-text-field
                        v-model.number="magicCastle.storage[`${id}_size`]"
                        type="number"
                        suffix="GB"
                        :rules="[volumeCountRule, volumeSizeRule, greaterThanZeroRule]"
                      />
                    </v-col>
                  </v-list-item>
                  <v-divider />
                </div>
                <v-list-item>
                  <v-col cols="12" sm="6">
                    <resource-usage-display
                      :max="volumeCountMax"
                      :used="volumeCountUsed"
                      title="volumes"
                    />
                  </v-col>
                  <v-col cols="12" sm="6">
                    <resource-usage-display
                      :max="volumeSizeMax"
                      :used="volumeSizeUsed"
                      title="volume storage"
                      suffix="GB"
                    />
                  </v-col>
                </v-list-item>
                <v-divider />
              </v-list>

              <!-- Networking & security -->
              <v-subheader>Networking and security</v-subheader>
              <v-list>
                <v-list-item>
                  <public-key-input v-model="mainPublicKey" />
                </v-list-item>
                <v-list-item>
                  <v-text-field
                    v-model="magicCastle.guest_passwd"
                    label="Guest password (optional)"
                    :rules="[passwordLengthRule]"
                  />
                </v-list-item>
                <v-list-item>
                  <v-select
                    :items="getPossibleValues('os_floating_ips')"
                    v-model="magicCastle.os_floating_ips[0]"
                    :rules="[floatingIpRule]"
                    label="OpenStack floating IP"
                  />
                </v-list-item>
              </v-list>
              <div class="text-center">
                <p v-if="!validForm" class="error--text">Some form fields are invalid.</p>
                <template v-if="existingCluster">
                  <v-btn
                    @click="planModification"
                    color="primary"
                    class="ma-2"
                    :disabled="loading || !validForm"
                    large
                  >Modify</v-btn>
                  <v-btn
                    @click="planDestruction"
                    color="primary"
                    class="ma-2"
                    :disabled="loading"
                    large
                    outlined
                  >Destroy</v-btn>
                </template>
                <template v-else>
                  <v-btn
                    @click="planCreation"
                    color="primary"
                    :disabled="loading || !validForm"
                    large
                  >Spawn</v-btn>
                </template>
              </div>
            </template>
            <template
              v-else-if="resourcesChanges && (currentStatus == 'build_running' || currentStatus == 'destroy_running')"
            >
              <v-divider />
              <cluster-resources
                :resources-changes="resourcesChanges"
                @updateProgress="updateProgress"
                show-progress
              />
            </template>
          </v-form>
        </v-card-text>
      </v-card>
    </v-container>
    <message-dialog v-model="successDialog" type="success">
      Your cluster was created successfully.
      <br />
      <br />Don't forget to destroy it when you are done!
    </message-dialog>
    <message-dialog v-model="errorDialog" type="error">{{ errorMessage }}</message-dialog>
    <message-dialog
      v-model="clusterPlanRunningDialog"
      type="loading"
      no-close
      persistent
    >Generating resource plan... please wait.</message-dialog>
    <confirm-dialog
      encourage-confirm
      :max-width="550"
      title="Build confirmation"
      v-model="clusterModificationDialog"
      @confirm="applyCluster"
    >
      Are you sure you want to apply the following actions?
      <cluster-resources
        :resources-changes="resourcesChanges"
        style="max-height: calc(80vh - 200px)"
        class="overflow-y-auto"
      />
    </confirm-dialog>
    <confirm-dialog
      alert
      encourage-cancel
      :max-width="550"
      title="Destruction confirmation"
      v-model="clusterDestructionDialog"
      @confirm="applyCluster"
    >
      Are you sure you want to permanently destroy your cluster and all its data?
      <cluster-resources
        :resources-changes="resourcesChanges"
        style="max-height: calc(80vh - 200px)"
        class="overflow-y-auto"
      />
    </confirm-dialog>
  </div>
</template>

<script>
import { cloneDeep } from "lodash";
import MagicCastleRepository from "@/repositories/MagicCastleRepository";
import AvailableResourcesRepository from "@/repositories/AvailableResourcesRepository";
import ClusterStatusCode from "@/models/ClusterStatusCode";
import ResourceUsageDisplay from "@/components/ui/ResourceUsageDisplay";
import StatusChip from "@/components/ui/StatusChip";
import PublicKeyInput from "@/components/ui/PublicKeyInput";
import MessageDialog from "@/components/ui/MessageDialog";
import ConfirmDialog from "@/components/ui/ConfirmDialog";
import ClusterResources from "@/components/cluster/ClusterResources";

const DEFAULT_MAGIC_CASTLE = Object.freeze({
  cluster_name: "phoenix",
  domain: "calculquebec.cloud",
  image: "CentOS-7-x64-2019-07",
  nb_users: 10,
  instances: {
    mgmt: {
      type: "p4-6gb",
      count: 1
    },
    login: {
      type: "p2-3gb",
      count: 1
    },
    node: {
      type: "p2-3gb",
      count: 1
    }
  },
  storage: {
    type: "nfs",
    home_size: 100,
    project_size: 50,
    scratch_size: 50
  },
  public_keys: [],
  guest_passwd: "",
  os_floating_ips: []
});

const EXTERNAL_STORAGE_VOLUME_COUNT = 3;
const MB_PER_GB = 1024;
const MINIMUM_PASSWORD_LENGTH = 8;
const POLL_STATUS_INTERVAL = 1000;

export default {
  name: "ClusterEditor",
  components: {
    ConfirmDialog,
    MessageDialog,
    StatusChip,
    ResourceUsageDisplay,
    PublicKeyInput,
    ClusterResources
  },
  props: {
    hostname: String,
    existingCluster: {
      type: Boolean,
      required: true
    },
    showPlanConfirmation: {
      type: Boolean,
      default: false
    },
    destroy: {
      type: Boolean,
      default: false
    }
  },
  data: function() {
    return {
      NODE_LABELS: {
        mgmt: "Management",
        login: "Login",
        node: "Compute"
      },
      STORAGE_LABELS: {
        home: "Home",
        project: "Project",
        scratch: "Scratch"
      },

      validForm: true,
      dirtyForm: false,

      progress: 0,
      successDialog: false,
      errorDialog: false,
      clusterDestructionDialog: false,
      clusterPlanRunningDialog: false,
      clusterModificationDialog: false,
      errorMessage: "",
      statusPoller: null,
      currentStatus: null,
      resourcesChanges: [],
      magicCastle: null,
      magicCastleInitialized: false,
      quotas: null,
      resourceDetails: null,
      possibleResources: null,
      mainPublicKey: "",

      clusterNameRegexRule: value =>
        value.match(/^[a-z][a-z0-9]*$/) !== null ||
        "The cluster name must have only lowercase alphanumeric characters and start with a letter",
      greaterThanZeroRule: value =>
        (typeof value === "number" && value > 0) || "Must be greater than zero",
      positiveNumberRule: value =>
        (typeof value === "number" && value >= 0) ||
        "Must be a positive number",
      passwordLengthRule: value =>
        value.length === 0 ||
        value.length >= MINIMUM_PASSWORD_LENGTH ||
        `The password must be at least ${MINIMUM_PASSWORD_LENGTH} characters long`
    };
  },
  async created() {
    if (this.existingCluster) {
      if (this.showPlanConfirmation) {
        await this.showPlanConfirmationDialog();
      } else if (this.destroy) {
        await this.planDestruction();
      }
      this.startStatusPolling();
    } else {
      this.magicCastle = cloneDeep(DEFAULT_MAGIC_CASTLE);
      await this.loadAvailableResources();
      if (this.possibleResources.os_floating_ips.length === 0) {
        this.showError("There is no floating IP available right now.");
        return;
      }
      this.magicCastle.os_floating_ips = [
        this.possibleResources.os_floating_ips[0]
      ];
    }
    // Wait for magicCastle watcher to finish executing
    this.$nextTick(() => {
      this.magicCastleInitialized = true;
    });
  },
  beforeDestroy() {
    this.stopStatusPolling();
  },
  computed: {
    loading() {
      const clusterIsBusy = [
        ClusterStatusCode.DESTROY_RUNNING,
        ClusterStatusCode.BUILD_RUNNING
      ].includes(this.currentStatus);
      const existingClusterIsLoading =
        this.existingCluster && (this.currentStatus === null || clusterIsBusy);
      return this.possibleResources === null || existingClusterIsLoading;
    },
    clusterName() {
      return this.hostname.split(".")[0];
    },
    instanceRules() {
      return [
        this.ramGbUsed <= this.ramGbMax || "Ram exceeds maximum",
        this.vcpuUsed <= this.vcpuMax || "Cores exceeds maximum"
      ];
    },
    volumeCountRule() {
      return (
        this.volumeCountUsed <= this.volumeCountMax ||
        "Number of volumes exceeds maximum"
      );
    },
    volumeSizeRule() {
      return (
        this.volumeSizeUsed <= this.volumeSizeMax ||
        "Volume storage exceeds maximum"
      );
    },
    floatingIpRule() {
      return (
        this.magicCastle.os_floating_ips.length > 0 ||
        "No OpenStack floating IP provided"
      );
    },
    instanceCountUsed() {
      if (!this.magicCastle || !this.resourceDetails) return 0;
      const instances = Object.values(this.magicCastle.instances);
      return instances.reduce((acc, instance) => acc + instance.count, 0);
    },
    instanceCountMax() {
      if (!this.quotas) return 0;
      return this.quotas.instance_count.max;
    },
    ramGbUsed() {
      if (!this.magicCastle || !this.resourceDetails) return 0;
      const instances = Object.values(this.magicCastle.instances);
      return (
        instances.reduce(
          (acc, instance) =>
            acc + instance.count * this.getInstanceDetail(instance.type, "ram"),
          0
        ) / MB_PER_GB
      );
    },
    ramGbMax() {
      if (!this.quotas) return 0;
      return this.quotas.ram.max / MB_PER_GB;
    },
    vcpuUsed() {
      if (!this.magicCastle || !this.resourceDetails) return 0;
      const instances = Object.values(this.magicCastle.instances);
      return instances.reduce(
        (acc, instance) =>
          acc + instance.count * this.getInstanceDetail(instance.type, "vcpus"),
        0
      );
    },
    vcpuMax() {
      if (!this.quotas) return 0;
      return this.quotas.vcpus.max;
    },
    volumeCountUsed() {
      if (!this.magicCastle || !this.resourceDetails) return 0;
      const instances = Object.values(this.magicCastle.instances);
      return (
        instances.reduce(
          (acc, instance) =>
            acc +
            instance.count *
              this.getInstanceDetail(instance.type, "required_volume_count"),
          0
        ) + EXTERNAL_STORAGE_VOLUME_COUNT
      );
    },
    volumeCountMax() {
      if (!this.quotas) return 0;
      return this.quotas.volume_count.max;
    },
    volumeSizeUsed() {
      if (!this.magicCastle || !this.resourceDetails) return 0;
      const instances = Object.values(this.magicCastle.instances);

      // storage required by nodes
      let storage = instances.reduce(
        (acc, instance) =>
          acc +
          instance.count *
            this.getInstanceDetail(instance.type, "required_volume_size"),
        0
      );
      storage += this.magicCastle.storage.home_size;
      storage += this.magicCastle.storage.project_size;
      storage += this.magicCastle.storage.scratch_size;
      return storage;
    },
    volumeSizeMax() {
      if (!this.quotas) return 0;
      return this.quotas.volume_size.max;
    }
  },
  watch: {
    magicCastle: {
      handler() {
        if (this.magicCastleInitialized) {
          this.dirtyForm = true;
        }
      },
      deep: true
    },
    dirtyForm(dirty) {
      if (dirty) {
        this.$enableUnloadConfirmation();
      } else {
        this.$disableUnloadConfirmation();
      }
    },
    mainPublicKey(mainPublicKey) {
      if (mainPublicKey.length === 0) {
        this.magicCastle.public_keys = [];
      } else {
        this.magicCastle.public_keys = [mainPublicKey];
      }
    }
  },
  methods: {
    updateProgress(progress) {
      this.progress = progress;
    },
    getPossibleValues(fieldPath) {
      if (this.possibleResources === null) {
        return [];
      } else {
        return fieldPath
          .split(".")
          .reduce((acc, x) => acc[x], this.possibleResources);
      }
    },
    getInstanceDetail(instanceType, detailName, defaultValue = 0) {
      const matchingInstances = this.resourceDetails.instance_types.filter(
        instanceTypeDetails => instanceTypeDetails.name === instanceType
      );
      if (matchingInstances.length > 0) {
        return matchingInstances[0][detailName];
      } else {
        return defaultValue;
      }
    },
    showSuccess() {
      this.successDialog = true;
    },
    showError(message) {
      this.errorDialog = true;
      this.errorMessage = message;
    },
    startStatusPolling() {
      let fetchStatus = async () => {
        const { status, progress } = (
          await MagicCastleRepository.getStatus(this.hostname)
        ).data;
        const statusChanged = this.currentStatus !== status;
        if (this.currentStatus && statusChanged) {
          this.showStatusDialog(status);
        }
        this.currentStatus = status;
        this.resourcesChanges = progress || [];
        if (statusChanged) {
          const clusterIsBusy = [
            ClusterStatusCode.PLAN_RUNNING,
            ClusterStatusCode.DESTROY_RUNNING,
            ClusterStatusCode.BUILD_RUNNING
          ].includes(status);
          if (!clusterIsBusy) {
            this.stopStatusPolling();
            if (status == ClusterStatusCode.NOT_FOUND) {
              this.unloadCluster();
              this.$router.push("/");
            } else {
              await Promise.all([
                this.loadAvailableResources(),
                this.loadCluster()
              ]);
            }
          }
        }
      };

      this.statusPoller = setInterval(fetchStatus, POLL_STATUS_INTERVAL);
      fetchStatus();
    },
    stopStatusPolling() {
      clearInterval(this.statusPoller);
    },
    showStatusDialog(status) {
      switch (status) {
        case ClusterStatusCode.BUILD_SUCCESS:
          this.showSuccess();
          break;
        case ClusterStatusCode.IDLE:
          this.showError("The server is still idle");
          break;
        case ClusterStatusCode.BUILD_ERROR:
          this.showError("An error occurred while creating the cluster.");
          break;
        case ClusterStatusCode.DESTROY_ERROR:
          this.showError("An error occurred while destroying the cluster.");
      }
    },
    async loadAvailableResources() {
      let availableResources = undefined;
      try {
        availableResources = this.existingCluster
          ? (await AvailableResourcesRepository.get(this.hostname)).data
          : (await AvailableResourcesRepository.get()).data;
      } catch (e) {
        availableResources = (await AvailableResourcesRepository.get()).data;
      }
      this.possibleResources = availableResources.possible_resources;
      this.quotas = availableResources.quotas;
      this.resourceDetails = availableResources.resource_details;
    },
    async loadCluster() {
      try {
        this.magicCastleInitialized = false;
        this.magicCastle = (
          await MagicCastleRepository.getState(this.hostname)
        ).data;
      } catch (e) {
        // Terraform state file could not be parsed or was not created.
        // This happens for new clusters, which are not built yet.
        this.magicCastle = cloneDeep(DEFAULT_MAGIC_CASTLE);
      } finally {
        if (this.magicCastle.public_keys.length > 0)
          this.mainPublicKey = this.magicCastle.public_keys[0];

        // Wait for magicCastle watcher to finish executing
        this.$nextTick(() => {
          this.magicCastleInitialized = true;
        });
      }
    },
    async planCreation() {
      try {
        this.clusterPlanRunningDialog = true;
        await MagicCastleRepository.create(this.magicCastle);
        this.$disableUnloadConfirmation();
        await this.$router.push({
          path: `/clusters/${this.magicCastle.cluster_name}.${this.magicCastle.domain}`,
          query: { showPlanConfirmation: "1" }
        });
        this.unloadCluster();
      } catch (e) {
        this.showError(e.response.data.message);
      } finally {
        this.clusterPlanRunningDialog = false;
      }
    },
    async planModification() {
      let planCreator = () =>
        MagicCastleRepository.update(this.hostname, this.magicCastle);
      await this.showPlanConfirmationDialog({ planCreator });
    },
    async planDestruction() {
      let planCreator = () => MagicCastleRepository.delete(this.hostname);
      await this.showPlanConfirmationDialog({ planCreator, destroy: true });
    },
    async applyCluster() {
      try {
        await MagicCastleRepository.apply(this.hostname);
        this.unloadCluster();
        this.startStatusPolling();
      } catch (e) {
        this.showError(e.response.data.message);
      }
    },
    async showPlanConfirmationDialog(
      options = { planCreator: async () => {}, destroy: false }
    ) {
      this.resourcesChanges = [];
      try {
        // Create plan
        this.clusterPlanRunningDialog = true;
        await options.planCreator();

        // Fetch plan
        const { progress } = (
          await MagicCastleRepository.getStatus(this.hostname)
        ).data;
        this.resourcesChanges = progress || [];
        this.clusterPlanRunningDialog = false;

        // Display plan
        if (options.destroy === true) {
          this.clusterDestructionDialog = true;
        } else {
          this.clusterModificationDialog = true;
        }
      } catch (e) {
        this.clusterPlanRunningDialog = false;
        this.showError(e.response.data.message);
      }
    },
    unloadCluster() {
      this.magicCastle = null;
      this.currentStatus = null;
      this.dirtyForm = false;
      this.magicCastleInitialized = false;
    }
  }
};
</script>
