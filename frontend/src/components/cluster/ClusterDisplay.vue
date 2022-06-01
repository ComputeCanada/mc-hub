<template>
  <div>
    <v-container>
      <v-card max-width="800" class="mx-auto" :loading="loading">
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
              <status-chip :status="status" />
            </v-list-item>
            <v-list-item v-if="cloud_id">
              <v-list-item-content>
                <v-list-item-subtitle>Cloud project</v-list-item-subtitle>
                <v-list-item-title>{{ cloud_id }}</v-list-item-title>
              </v-list-item-content>
            </v-list-item>
            <v-divider class="mt-2" v-if="resourcesChanges.length > 0 || magicCastle" />
          </v-list>
          <cluster-editor
            v-if="magicCastle && !applyRunning && !clusterDestructionDialog"
            :existing-cluster="existingCluster"
            :specs="magicCastle"
            :status="status"
            v-on="{ apply: existingCluster ? planModification : planCreation }"
            @loading="loading = $event"
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
    <message-dialog v-model="provisioningRunningDialog" type="success" :callback="goHome">
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
import ClusterStatusCode from "@/models/ClusterStatusCode";
import MessageDialog from "@/components/ui/MessageDialog";
import StatusChip from "@/components/ui/StatusChip";
import ConfirmDialog from "@/components/ui/ConfirmDialog";
import ClusterResources from "@/components/cluster/ClusterResources";
import ClusterEditor from "@/components/cluster/ClusterEditor";
import { isEqual } from "lodash";

const DEFAULT_MAGIC_CASTLE = Object.freeze({
  cluster_name: "",
  domain: null,
  image: null,
  nb_users: 10,
  instances: {
    mgmt: {
      type: null,
      count: 1,
      tags: ["mgmt", "nfs", "puppet"],
    },
    login: {
      type: null,
      count: 1,
      tags: ["login", "proxy", "public"],
    },
    node: {
      type: null,
      count: 1,
      tags: ["node"],
    },
  },
  volumes: {
    nfs: {
      home: { size: 100 },
      project: { size: 50 },
      scratch: { size: 50 },
    },
  },
  public_keys: [],
  guest_passwd: "",
  hieradata: "",
});

const POLL_STATUS_INTERVAL = 1000;

export default {
  name: "ClusterDisplay",
  components: {
    StatusChip,
    ClusterEditor,
    ConfirmDialog,
    MessageDialog,
    ClusterResources,
  },
  props: {
    hostname: String,
    showPlanConfirmation: {
      type: Boolean,
      default: false,
    },
    destroy: {
      type: Boolean,
      default: false,
    },
  },
  data: function () {
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
      status: null,
      resourcesChanges: [],
      magicCastle: null,
      loading: false,
      statusPromise: null,
    };
  },
  async created() {
    if (this.existingCluster) {
      if (this.showPlanConfirmation) {
        await this.showPlanConfirmationDialog();
      } else if (this.destroy) {
        const { status } = (await MagicCastleRepository.getStatus(this.hostname)).data;
        if (status == ClusterStatusCode.CREATED || status == ClusterStatusCode.PLAN_ERROR) {
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
    }
  },
  beforeDestroy() {
    this.stopStatusPolling();
  },
  computed: {
    busy() {
      return [
        ClusterStatusCode.DESTROY_RUNNING,
        ClusterStatusCode.BUILD_RUNNING,
        ClusterStatusCode.PLAN_RUNNING,
      ].includes(this.status);
    },
    applyRunning() {
      return [ClusterStatusCode.DESTROY_RUNNING, ClusterStatusCode.BUILD_RUNNING].includes(this.status);
    },
    cloud_id() {
      try {
        return this.magicCastle.cloud_id;
      } catch (e) {
        return null;
      }
    },
    existingCluster() {
      return this.hostname !== null && this.hostname !== undefined;
    },
  },
  methods: {
    goHome() {
      this.unloadCluster();
      this.$router.push("/");
    },
    updateProgress(progress) {
      this.progress = progress;
    },
    async fetchStatus() {
      if (this.statusPromise !== null) {
        return;
      }
      const statusAlreadyInitialized = this.status !== null;
      const planWasRunning = this.status === ClusterStatusCode.PLAN_RUNNING;

      this.statusPromise = MagicCastleRepository.getStatus(this.hostname);
      const { status, progress } = (await this.statusPromise).data;
      this.statusPromise = null;
      this.status = status;
      this.resourcesChanges = progress || [];

      if (!this.busy) {
        this.stopStatusPolling();
        if (statusAlreadyInitialized && !planWasRunning) {
          // We avoid displaying any status dialog after plan generation,
          // because the new status may be the same as before the plan creation.
          this.showStatusDialog();
        }
        if (status == ClusterStatusCode.NOT_FOUND) {
          this.goHome();
        } else {
          await this.loadCluster();
        }
      }
    },
    startStatusPolling() {
      this.statusPoller = setInterval(this.fetchStatus, POLL_STATUS_INTERVAL);
      this.fetchStatus();
    },
    stopStatusPolling() {
      clearInterval(this.statusPoller);
    },
    showStatusDialog() {
      switch (this.status) {
        case ClusterStatusCode.PROVISIONING_RUNNING:
          this.provisioningRunningDialog = true;
          break;
        // case ClusterStatusCode.PROVISIONING_SUCCESS:
        // this.successDialog = true;
        // break;
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
    async loadCluster() {
      try {
        this.magicCastle = (await MagicCastleRepository.getState(this.hostname)).data;
      } catch (e) {
        // Terraform state file and main.tf.json could not be parsed.
        this.showError(e.response.data.message);
      }
    },
    async planCreation() {
      let isCommited = false;
      let showPlan = "0";
      this.clusterPlanRunningDialog = true;
      try {
        await MagicCastleRepository.create(this.magicCastle);
        isCommited = true;
        showPlan = "1";
      } catch (error) {
        if (error.response) {
          this.showError(error.response.data.message);
          isCommited = true;
        } else if (error.request) {
          console.log(error.request);
          this.showError("Plan creation request was made but no response was received.");
        } else {
          console.log(error.message);
          this.showError("Plan creation request setting up triggered an error.");
        }
      } finally {
        this.$disableUnloadConfirmation();
        if (isCommited) {
          await this.$router.push({
            path: `/clusters/${this.magicCastle.cluster_name}.${this.magicCastle.domain}`,
            query: { showPlanConfirmation: showPlan },
          });
          this.unloadCluster();
        }
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
      } catch (e) {
        this.showError(e.response.data.message);
      }
    },
    async applyCluster() {
      try {
        await MagicCastleRepository.apply(this.hostname);
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
        destroy: false,
      }
    ) {
      this.resourcesChanges = [];
      try {
        // Create plan
        this.clusterPlanRunningDialog = true;
        await options.planCreator();

        // Fetch plan
        const { message, progress } = (await MagicCastleRepository.getStatus(this.hostname)).data;
        this.resourcesChanges = progress.filter((resource) => !isEqual(resource.change.actions, ["no-op"])) || [];
        this.clusterPlanRunningDialog = false;

        // Display plan
        if (message) {
          this.showError(message);
        } else if (options.destroy === true) {
          this.clusterDestructionDialog = true;
        } else if (this.resourcesChanges.length !== 0) {
          this.clusterModificationDialog = true;
        } else {
          this.applyCluster();
        }
      } catch (e) {
        this.clusterPlanRunningDialog = false;
        this.showError(e.response.data.message);
      }
    },
    unloadCluster() {
      this.magicCastle = null;
      this.status = null;
    },
  },
};
</script>
