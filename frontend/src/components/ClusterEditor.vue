<template>
  <div>
    <v-container>
      <v-card max-width="500" class="mx-auto" :loading="loading">
        <v-card-title v-if="existingCluster" class="mx-auto pl-8">
          Magic Castle Modification
        </v-card-title>
        <v-card-title v-else class="mx-auto pl-8">
          Magic Castle Creation
        </v-card-title>
        <v-card-text>
          <v-form ref="form" v-model="validForm">
            <v-subheader>General configuration</v-subheader>
            <v-list class="pb-0">
              <v-list-item>
                <div style="display: flex; align-items: center; width: 100%">
                  <v-text-field v-if="existingCluster" v-model="clusterName" label="Cluster name" disabled />
                  <v-text-field v-else v-model="magicCastle.cluster_name" label="Cluster name" />
                  <v-chip class="ml-3" label :color="formattedStatus.color" dark v-if="currentStatus !== null"
                    >{{ formattedStatus.text }}
                  </v-chip>
                </div>
              </v-list-item>
            </v-list>
            <template v-if="magicCastle !== null">
              <v-list class="pt-0">
                <v-list-item>
                  <v-text-field v-model="magicCastle.domain" label="Domain" />
                </v-list-item>
                <v-list-item>
                  <v-select v-model="magicCastle.image" :items="getPossibleValues('image')" label="Image" />
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
                  <v-col cols="12" sm="6">
                    <resource-usage-display :max="ramGbMax" :used="ramGbUsed" title="RAM" suffix="GB" />
                  </v-col>
                  <v-col cols="12" sm="6">
                    <resource-usage-display :max="vcpuMax" :used="vcpuUsed" title="cores" />
                  </v-col>
                </v-list-item>
                <v-divider />
              </v-list>

              <!-- Storage -->
              <v-subheader>Storage</v-subheader>
              <v-list>
                <v-list-item>
                  <v-col cols="12" sm="3" class="pl-0">
                    Type
                  </v-col>
                  <v-col cols="12" sm="9">
                    <v-select :items="getPossibleValues('storage.type')" v-model="magicCastle.storage.type" />
                  </v-col>
                </v-list-item>
                <v-divider />
                <div :key="id" v-for="[id, label] in Object.entries(STORAGE_LABELS)">
                  <v-list-item>
                    <v-col cols="12" sm="3" class="pl-0"> {{ label }} size</v-col>
                    <v-col cols="12" sm="9">
                      <v-text-field
                        v-model.number="magicCastle.storage[`${id}_size`]"
                        type="number"
                        suffix="GB"
                        :rules="[storageRule, greaterThanZeroRule]"
                      />
                    </v-col>
                  </v-list-item>
                  <v-divider />
                </div>
                <v-list-item>
                  <v-col cols="12">
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
                  <v-file-input ref="a" @change="publicKeysUpdated" label="SSH public key file" />
                </v-list-item>
                <v-list-item>
                  <v-text-field v-model="magicCastle.guest_passwd" label="Guest password (optional)" />
                </v-list-item>
                <v-list-item>
                  <v-select
                    :items="getPossibleValues('os_floating_ips')"
                    v-model="magicCastle.os_floating_ips[0]"
                    :rules="[floatingIpRule]"
                    label="OpenStack floating IP (optional)"
                  />
                </v-list-item>
              </v-list>
              <div class="text-center">
                <p v-if="!validForm" class="error--text">Some form fields are invalid.</p>
                <template v-if="existingCluster === true">
                  <v-btn @click="modifyCluster" color="primary" class="ma-2" :disabled="loading || !validForm" large>
                    Modify
                  </v-btn>
                  <v-btn @click="deleteCluster" color="primary" class="ma-2" :disabled="loading" large outlined>
                    Delete
                  </v-btn>
                </template>
                <template v-else>
                  <v-btn
                    @click="createCluster"
                    color="primary"
                    class="text-right"
                    :disabled="loading || !validForm"
                    large
                    >Spawn
                  </v-btn>
                </template>
              </div>
            </template>
          </v-form>
        </v-card-text>
      </v-card>
    </v-container>
    <v-dialog v-model="successDialog" max-width="400">
      <v-card>
        <v-card-title>Success</v-card-title>
        <v-card-text>
          Your cluster was created successfully.<br /><br />
          Don't forget to destroy it when you are done!
        </v-card-text>
        <v-divider></v-divider>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="primary" text @click="successDialog = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
    <v-dialog v-model="errorDialog" max-width="400">
      <v-card>
        <v-card-title>Error</v-card-title>
        <v-card-text>
          {{ errorMessage }}
        </v-card-text>
        <v-divider></v-divider>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="primary" text @click="errorDialog = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script>
import MagicCastleRepository from "@/repositories/MagicCastleRepository";
import AvailableResourcesRepository from "@/repositories/AvailableResourcesRepository";
import ResourceUsageDisplay from "./ResourceUsageDisplay";

const ClusterStatusCode = Object.freeze({
  IDLE: "idle",
  BUILD_RUNNING: "build_running",
  BUILD_SUCCESS: "build_success",
  BUILD_ERROR: "build_error",
  DESTROY_RUNNING: "destroy_running",
  DESTROY_ERROR: "destroy_error",
  NOT_FOUND: "not_found"
});

const ClusterFormattedStatus = Object.freeze({
  idle: { text: "Idle", color: "blue" },
  build_running: { text: "Build running", color: "orange" },
  build_success: { text: "Build success", color: "green" },
  build_error: { text: "Build error", color: "red" },
  destroy_running: { text: "Destroy running", color: "orange" },
  destroy_error: { text: "Destroy error", color: "red" },
  not_found: { text: "Not found", color: "purple" }
});

const POLL_STATUS_INTERVAL = 1000;

const DEFAULT_MAGIC_CASTLE = {
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
};

const MB_PER_GB = 1024;

export default {
  name: "ClusterEditor",
  components: { ResourceUsageDisplay },
  props: {
    clusterName: String,
    existingCluster: {
      type: Boolean,
      required: true
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
      successDialog: false,
      errorDialog: false,
      errorMessage: "",
      statusPoller: null,
      currentStatus: null,
      magicCastle: null,
      quotas: null,
      resourceDetails: null,
      possibleResources: null,

      greaterThanZeroRule: value => (typeof value === "number" && value > 0) || "Must be greater than zero",
      positiveNumberRule: value => (typeof value === "number" && value >= 0) || "Must be a positive number"
    };
  },
  async created() {
    if (this.existingCluster) {
      this.startStatusPolling();
    } else {
      this.magicCastle = DEFAULT_MAGIC_CASTLE;
      await this.loadAvailableResources();
      if (this.possibleResources.os_floating_ips.length === 0) {
        this.showError("There is no floating IP available right now.");
      } else {
        this.magicCastle.os_floating_ips = [this.possibleResources.os_floating_ips[0]];
      }
    }
  },
  beforeDestroy() {
    this.stopStatusPolling();
  },
  computed: {
    loading() {
      const clusterIsBusy = [ClusterStatusCode.DESTROY_RUNNING, ClusterStatusCode.BUILD_RUNNING].includes(
        this.currentStatus
      );
      const existingClusterIsLoading = this.existingCluster && (this.currentStatus === null || clusterIsBusy);
      return this.possibleResources === null || existingClusterIsLoading;
    },
    formattedStatus() {
      if (this.currentStatus === null) {
        return ClusterFormattedStatus[ClusterStatusCode.IDLE];
      } else {
        return ClusterFormattedStatus[this.currentStatus];
      }
    },
    instanceRules() {
      return [
        this.ramGbUsed <= this.ramGbMax || "Ram exceeds maximum",
        this.vcpuUsed <= this.vcpuMax || "Cores exceeds maximum"
      ];
    },
    storageRule() {
      return this.volumeSizeUsed <= this.volumeSizeMax || "Volume storage exceeds maximum";
    },
    floatingIpRule() {
      return this.magicCastle.os_floating_ips.length > 0 || "No OpenStack floating IP provided";
    },
    ramGbUsed() {
      if (!this.magicCastle || !this.resourceDetails) return 0;
      const instances = Object.values(this.magicCastle.instances);
      return (
        instances.reduce((acc, instance) => acc + instance.count * this.getInstanceDetail(instance.type, "ram"), 0) /
        MB_PER_GB
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
        (acc, instance) => acc + instance.count * this.getInstanceDetail(instance.type, "vcpus"),
        0
      );
    },
    vcpuMax() {
      if (!this.quotas) return 0;
      return this.quotas.vcpus.max;
    },
    volumeSizeUsed() {
      if (!this.magicCastle || !this.resourceDetails) return 0;
      const instances = Object.values(this.magicCastle.instances);

      // storage required by nodes
      let storage = instances.reduce(
        (acc, instance) => acc + instance.count * this.getInstanceDetail(instance.type, "required_volume_size"),
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
  methods: {
    getPossibleValues(fieldPath) {
      if (this.possibleResources === null) {
        return [];
      } else {
        return fieldPath.split(".").reduce((acc, x) => acc[x], this.possibleResources);
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
    publicKeysUpdated(file) {
      const reader = new FileReader();
      reader.addEventListener("load", event => {
        // The new lines (\n) at the end of ssh key files must be removed
        const publicKey = event.target.result.replace(/(\n)+$/, "");
        this.magicCastle.public_keys = [publicKey];
      });
      if (typeof file === "object") reader.readAsText(file);
      else this.magicCastle.public_keys = [];
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
        const { status } = (await MagicCastleRepository.getStatus(this.clusterName)).data;

        if (this.currentStatus !== status) {
          // The cluster status changed or was fetched for the first time
          const clusterIsBusy = [ClusterStatusCode.DESTROY_RUNNING, ClusterStatusCode.BUILD_RUNNING].includes(status);
          if (!clusterIsBusy) {
            this.loadAvailableResources();
            this.loadCluster();
          }
          if (this.currentStatus !== null) {
            this.showStatusDialog(status);
          }
        }
        this.currentStatus = status;
      };

      this.statusPoller = setInterval(fetchStatus, POLL_STATUS_INTERVAL);
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
          this.showError("Terraform returned an error while creating the cluster.");
          break;
        case ClusterStatusCode.DESTROY_ERROR:
          this.showError("Terraform returned an error while destroying the cluster.");
      }
    },
    stopStatusPolling() {
      clearInterval(this.statusPoller);
    },
    async loadAvailableResources() {
      const availableResources = this.existingCluster
        ? (await AvailableResourcesRepository.get(this.clusterName)).data
        : (await AvailableResourcesRepository.get()).data;
      this.possibleResources = availableResources.possible_resources;
      this.quotas = availableResources.quotas;
      this.resourceDetails = availableResources.resource_details;
    },
    async createCluster() {
      try {
        await MagicCastleRepository.create(this.magicCastle);
        await this.$router.push({ path: `/clusters/${this.magicCastle.cluster_name}` });
      } catch (e) {
        this.showError(e.response.data.message);
      }
    },
    async loadCluster() {
      try {
        this.magicCastle = (await MagicCastleRepository.getState(this.clusterName)).data;
      } catch (e) {
        console.log(e.response.data.message);
      }
    },
    async modifyCluster() {
      try {
        await MagicCastleRepository.update(this.clusterName, this.magicCastle);
        this.unloadCluster();
      } catch (e) {
        this.showError(e.response.data.message);
      }
    },
    async deleteCluster() {
      try {
        await MagicCastleRepository.delete(this.clusterName);
        this.unloadCluster();
      } catch (e) {
        this.showError(e.response.data.message);
      }
    },
    unloadCluster() {
      this.magicCastle = null;
      this.currentStatus = null;
    }
  }
};
</script>

<style scoped></style>
