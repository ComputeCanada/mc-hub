<template>
  <div>
    <v-container>
      <v-card max-width="650" class="mx-auto" :loading="loading">
        <template #progress>
          <v-progress-linear :indeterminate="progress === 0" :value="progress" />
        </template>
        <v-card-title v-if="existingCluster" class="mx-auto pl-8">Magic Castle Modification</v-card-title>
        <v-card-title v-else class="mx-auto pl-8">Magic Castle Creation</v-card-title>
        <v-card-text>
          <v-list v-if="existingCluster">
            <v-list-item>
              <v-list-item-content>
                <v-list-item-subtitle>Hostname</v-list-item-subtitle>
                <v-list-item-title>{{ hostname }}</v-list-item-title>
              </v-list-item-content>
              <status-chip :status="currentStatus" />
            </v-list-item>
            <v-divider class="mt-2" v-if="resourcesChanges.length > 0 || magicCastle" />
          </v-list>
          <cluster-editor
            v-if="magicCastle && !applyRunning"
            :loading="loading"
            :existing-cluster="existingCluster"
            :magic-castle="magicCastle"
            :current-status="currentStatus"
            :possible-resources="possibleResources"
            :resource-details="resourceDetails"
            :quotas="quotas"
            v-on="{ apply: existingCluster ? planModification : planCreation }"
          />
          <template v-else-if="resourcesChanges.length > 0 && applyRunning">
            <cluster-resources :resources-changes="resourcesChanges" @updateProgress="updateProgress" show-progress />
          </template>
        </v-card-text>
      </v-card>
    </v-container>
    <message-dialog v-model="successDialog" type="success">
      Your cluster was provisioned successfully.
      <br />
      <br />Don't forget to destroy it when you are done!
    </message-dialog>
    <message-dialog v-model="provisioningRunningDialog" type="success">
      The cloud resources have been allocated. Provisioning has started.
    </message-dialog>
    <message-dialog v-model="errorDialog" type="error">{{ errorMessage }}</message-dialog>
    <message-dialog v-model="clusterPlanRunningDialog" type="loading" no-close persistent
      >Generating resource plan... please wait.
    </message-dialog>
    <confirm-dialog
      encourage-confirm
      :max-width="650"
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
      :max-width="650"
      title="Destruction confirmation"
      v-model="clusterDestructionDialog"
      @confirm="applyCluster"
      @cancel="goToClustersList"
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
import MessageDialog from "@/components/ui/MessageDialog";
import StatusChip from "@/components/ui/StatusChip";
import ConfirmDialog from "@/components/ui/ConfirmDialog";
import ClusterResources from "@/components/cluster/ClusterResources";
import ClusterEditor from "@/components/cluster/ClusterEditor";

const DEFAULT_MAGIC_CASTLE = Object.freeze({
  cluster_name: "phoenix",
  domain: null,
  image: null,
  nb_users: 10,
  instances: {
    mgmt: {
      type: null,
      count: 1
    },
    login: {
      type: null,
      count: 1
    },
    node: {
      type: null,
      count: 1
    }
  },
  storage: {
    type: "nfs",
    home_size: 100,
    project_size: 50,
    scratch_size: 50
  },
  public_keys: [""],
  guest_passwd: "",
  hieradata: "",
  os_floating_ips: []
});

const POLL_STATUS_INTERVAL = 1000;

export default {
  name: "ClusterDisplay",
  components: {
    StatusChip,
    ClusterEditor,
    ConfirmDialog,
    MessageDialog,
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
      progress: 0,
      successDialog: false,
      provisioningRunningDialog: false,
      errorDialog: false,
      clusterDestructionDialog: false,
      clusterPlanRunningDialog: false,
      clusterModificationDialog: false,
      errorMessage: "",
      statusPoller: null,
      currentStatus: null,
      resourcesChanges: [],
      magicCastle: null,
      quotas: null,
      resourceDetails: null,
      possibleResources: null
    };
  },
  async created() {
    if (this.existingCluster) {
      if (this.showPlanConfirmation) {
        await this.showPlanConfirmationDialog();
      } else if (this.destroy) {
        const { status } = (await MagicCastleRepository.getStatus(this.hostname)).data;
        if (status == ClusterStatusCode.CREATED) {
          /* 
          The initial plan was created, but the cluster was never built.
          We don't show a confirmation because no resource has been created.
          */

          await this.forceDestruction();
        } else {
          await this.planDestruction();
        }
      }
      this.startStatusPolling();
    } else {
      this.magicCastle = cloneDeep(DEFAULT_MAGIC_CASTLE);
      await this.loadAvailableResources();
      if (this.possibleResources.os_floating_ips.length === 0) {
        this.showError("There is no floating IP available right now.");
      }
    }
  },
  beforeDestroy() {
    this.stopStatusPolling();
  },
  computed: {
    loading() {
      const existingClusterIsLoading = this.existingCluster && (this.currentStatus === null || this.busy);

      return !this.possibleResourcesLoaded || existingClusterIsLoading;
    },
    possibleResourcesLoaded() {
      return this.possibleResources !== null;
    },
    busy() {
      return [
        ClusterStatusCode.DESTROY_RUNNING,
        ClusterStatusCode.BUILD_RUNNING,
        ClusterStatusCode.PLAN_RUNNING
      ].includes(this.currentStatus);
    },
    requiresPolling() {
      return [
        ClusterStatusCode.DESTROY_RUNNING,
        ClusterStatusCode.BUILD_RUNNING,
        ClusterStatusCode.PROVISIONING_RUNNING,
        ClusterStatusCode.PLAN_RUNNING
      ].includes(this.currentStatus);
    },
    applyRunning() {
      return [ClusterStatusCode.DESTROY_RUNNING, ClusterStatusCode.BUILD_RUNNING].includes(this.currentStatus);
    }
  },
  methods: {
    updateProgress(progress) {
      this.progress = progress;
    },
    startStatusPolling() {
      let fetchStatus = async () => {
        const statusAlreadyInitialized = this.currentStatus !== null;
        const planWasRunning = this.currentStatus === ClusterStatusCode.PLAN_RUNNING;

        const { status, progress } = (await MagicCastleRepository.getStatus(this.hostname)).data;
        const statusChanged = status !== this.currentStatus;
        this.currentStatus = status;
        this.resourcesChanges = progress || [];

        if (statusChanged) {
          if (statusAlreadyInitialized && !planWasRunning) {
            // We avoid displaying any status dialog after plan generation,
            // because the new status may be the same as before the plan creation.
            this.showStatusDialog();
          }
          if (!this.requiresPolling) {
            this.stopStatusPolling();
          }
          if (!this.busy) {
            if (status == ClusterStatusCode.NOT_FOUND) {
              this.unloadCluster();
              this.$router.push("/");
            } else {
              await Promise.all([this.loadAvailableResources(), this.loadCluster()]);
            }
          }
        }
      };

      // Avoid two status pollers running concurrently
      this.stopStatusPolling();

      this.statusPoller = setInterval(fetchStatus, POLL_STATUS_INTERVAL);
      fetchStatus();
    },
    stopStatusPolling() {
      clearInterval(this.statusPoller);
    },
    showStatusDialog() {
      switch (this.currentStatus) {
        case ClusterStatusCode.PROVISIONING_RUNNING:
          this.provisioningRunningDialog = true;
          break;
        case ClusterStatusCode.PROVISIONING_SUCCESS:
          this.successDialog = true;
          break;
        case ClusterStatusCode.BUILD_ERROR:
          this.errorDialog = true;
          this.showError("An error occurred while creating the cluster.");
          break;
        case ClusterStatusCode.PROVISIONING_ERROR:
          this.errorDialog = true;
          this.showError("An error occurred while provisioning the cluster.");
          break;
        case ClusterStatusCode.DESTROY_ERROR:
          this.errorDialog = true;
          this.showError("An error occurred while destroying the cluster.");
      }
    },
    showError(message) {
      this.errorDialog = true;
      this.errorMessage = message;
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
        this.magicCastle = (await MagicCastleRepository.getState(this.hostname)).data;
      } catch (e) {
        // Terraform state file and main.tf.json could not be parsed.
        this.showError(e.response.data.message);
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
      let planCreator = async () => MagicCastleRepository.update(this.hostname, this.magicCastle);
      await this.showPlanConfirmationDialog({ planCreator });
    },
    async planDestruction() {
      let planCreator = async () => MagicCastleRepository.delete(this.hostname);
      await this.showPlanConfirmationDialog({ planCreator, destroy: true });
    },
    async forceDestruction() {
      try {
        this.unloadCluster();
        await MagicCastleRepository.delete(this.hostname);
        await MagicCastleRepository.apply(this.hostname);
        this.startStatusPolling();
      } catch (e) {
        this.showError(e.response.data.message);
      }
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
    async goToClustersList() {
      await this.$router.push("/");
    },
    async showPlanConfirmationDialog(
      options = {
        planCreator: async () => {},
        destroy: false
      }
    ) {
      this.resourcesChanges = [];
      try {
        // Create plan
        this.clusterPlanRunningDialog = true;
        await options.planCreator();

        // Fetch plan
        const { message, progress } = (await MagicCastleRepository.getStatus(this.hostname)).data;
        this.resourcesChanges = progress || [];
        this.clusterPlanRunningDialog = false;

        // Display plan
        if (message) {
          this.showError(message);
        } else if (options.destroy === true) {
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
    }
  }
};
</script>
