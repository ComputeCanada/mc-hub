<template>
  <div>
    <v-container>
      <v-card max-width="800" class="mx-auto" :loading="loading">
        <template #progress>
          <v-progress-linear :indeterminate="progress === 0" :value="progress" />
        </template>
        <v-card-title v-if="stateful" class="mx-auto pl-8">Magic Castle Modification</v-card-title>
        <v-card-title v-else class="mx-auto pl-8">Magic Castle Creation</v-card-title>
        <v-card-text>
          <v-list v-if="existingCluster">
            <v-list-item>
              <v-list-item-content>
                <v-list-item-subtitle>Hostname</v-list-item-subtitle>
                <v-list-item-title>{{ hostname }}</v-list-item-title>
              </v-list-item-content>
              <status-chip :status="status" :health="health" :undeployed="undeployed" />
            </v-list-item>
            <v-divider class="mt-2" v-if="resourcesChanges.length > 0 || magicCastle" />
          </v-list>
          <cluster-editor
            v-if="magicCastle && !busy && !clusterDestructionDialog"
            :existing-cluster="existingCluster"
            :specs="magicCastle"
            :status="status"
            :stateful="stateful"
            v-on="{ apply: existingCluster ? planModification : planCreation }"
            @rebuild="rebuildCluster"
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
      <br />Don't forget to tear it down when you are done!
    </message-dialog>
    <message-dialog v-model="provisioningRunningDialog" type="success" :callback="goHome">
      The cloud resources have been allocated. Provisioning has started.
    </message-dialog>
    <message-dialog v-model="errorDialog" type="error">{{ errorMessage }}</message-dialog>
    <message-dialog v-model="clusterPlanRunningDialog" type="loading" no-close persistent>
      <div v-if="creationStepIndex >= 0" aria-live="polite">
        <div v-for="(step, index) in creationSteps" :key="step.id" class="d-flex align-center my-3">
          <v-progress-circular
            v-if="index === creationStepIndex"
            indeterminate
            color="primary"
            :size="20"
            :width="2"
            class="mr-3 flex-shrink-0"
          />
          <v-icon v-else :color="index < creationStepIndex ? 'success' : 'grey'" size="20" class="mr-3">
            {{ index < creationStepIndex ? "mdi-check-circle" : "mdi-circle-outline" }}
          </v-icon>
          <span>
            {{ step.label }}
            <span class="text-caption"
              >—
              {{ index < creationStepIndex ? "Done" : index === creationStepIndex ? "In progress" : "Pending" }}</span
            >
          </span>
        </div>
      </div>
      <span v-else>{{ clusterPlanMessage }}</span>
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
      title="Delete"
      v-model="permanentDestructionDialog"
      alert
      encourage-cancel
      @confirm="forceDestruction"
      @cancel="goToClustersList"
    >
      Discard pending plans, remove this cluster from the UI, archive its GitHub repository, and mark its Terraform
      workspace as deleted?
    </confirm-dialog>
    <confirm-dialog
      alert
      encourage-cancel
      :max-width="650"
      title="Teardown confirmation"
      persistent
      v-model="clusterDestructionDialog"
      @confirm="applyCluster"
      @cancel="discardTeardown"
    >
      Delete this cluster’s deployed resources and their data? Keep its configuration, GitHub repository, and Terraform
      workspace so you can rebuild it later. Rebuilding does not restore deleted data.
      <cluster-resources
        :resources-changes="resourcesChanges"
        style="max-height: calc(80vh - 200px)"
        class="overflow-y-auto"
      />
    </confirm-dialog>
  </div>
</template>

<script>
import MagicCastleRepository from "@/repositories/MagicCastleRepository";
import TemplateRepository from "@/repositories/TemplateRepository";
import ClusterStatusCode, { canDestroyCluster } from "@/models/ClusterStatusCode";
import MessageDialog from "@/components/ui/MessageDialog";
import StatusChip from "@/components/ui/StatusChip";
import ConfirmDialog from "@/components/ui/ConfirmDialog";
import ClusterResources from "@/components/cluster/ClusterResources";
import ClusterEditor from "@/components/cluster/ClusterEditor";
import { isEqual } from "lodash";

const POLL_STATUS_INTERVAL = 1000;
const PLAN_START_TIMEOUT_MS = 1500;
const MAX_PLAN_WAIT_MS = 5 * 60 * 1000;

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
      permanentDestructionDialog: false,
      clusterPlanRunningDialog: false,
      creationStep: null,
      clusterPlanMessage: "Generating resource plan... please wait.",
      creationSteps: [
        { id: "github_repository", label: "Create GitHub repository" },
        { id: "terraform_workspace", label: "Create Terraform workspace" },
        { id: "variable_file", label: "Add variable file" },
        { id: "resource_plan", label: "Generate resource plan" },
      ],
      clusterModificationDialog: false,
      errorMessage: "",
      statusPoller: null,
      status: null,
      health: null,
      resourcesChanges: [],
      magicCastle: null,
      loading: false,
      statusPromise: null,
      applyRequested: false,
      stateful: false,
      undeployed: false,
    };
  },
  async created() {
    if (this.existingCluster) {
      if (this.showPlanConfirmation) {
        await this.showPlanConfirmationDialog();
      } else if (this.destroy) {
        const cluster = (await MagicCastleRepository.getStatus(this.hostname)).data;
        if (canDestroyCluster(cluster)) {
          this.permanentDestructionDialog = true;
        } else {
          await this.planDestruction();
        }
      }
      this.startStatusPolling();
    } else {
      this.magicCastle = (await TemplateRepository.get("default")).data;
    }
  },
  beforeDestroy() {
    this.stopStatusPolling();
  },
  computed: {
    creationStepIndex() {
      return this.creationSteps.findIndex((step) => step.id === this.creationStep);
    },
    busy() {
      return (
        this.applyRequested ||
        [ClusterStatusCode.DESTROY_RUNNING, ClusterStatusCode.BUILD_RUNNING, ClusterStatusCode.PLAN_RUNNING].includes(
          this.status
        )
      );
    },
    applyRunning() {
      return (
        this.applyRequested ||
        [ClusterStatusCode.DESTROY_RUNNING, ClusterStatusCode.BUILD_RUNNING].includes(this.status)
      );
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
      const applyWasRequested = this.applyRequested;

      this.statusPromise = MagicCastleRepository.getStatus(this.hostname);
      let response;
      try {
        response = await this.statusPromise;
      } finally {
        this.statusPromise = null;
      }
      // A poll started before confirmation must not overwrite the accepted plan.
      if (!applyWasRequested && this.applyRequested) {
        return;
      }
      const { status, health, stateful, progress, undeployed } = response.data;
      if (
        ![
          ClusterStatusCode.CREATED,
          ClusterStatusCode.PLAN_RUNNING,
          ClusterStatusCode.BUILD_RUNNING,
          ClusterStatusCode.DESTROY_RUNNING,
        ].includes(status)
      ) {
        this.applyRequested = false;
      }
      this.status = status;
      this.health = health;
      this.stateful = stateful;
      this.undeployed = undeployed === true;
      if (!this.applyRequested || progress?.length) {
        this.resourcesChanges = progress || [];
      }

      if (!this.busy) {
        this.stopStatusPolling();
        if ([ClusterStatusCode.DESTROY_SUCCESS, ClusterStatusCode.NOT_FOUND].includes(status)) {
          this.goHome();
          return;
        }
        if (applyWasRequested || (statusAlreadyInitialized && !planWasRunning)) {
          // We avoid displaying any status dialog after plan generation,
          // because the new status may be the same as before the plan creation.
          this.showStatusDialog();
        }
        await this.loadCluster();
      }
    },
    startStatusPolling() {
      this.stopStatusPolling();
      this.statusPoller = setInterval(this.fetchStatus, POLL_STATUS_INTERVAL);
      this.fetchStatus();
    },
    stopStatusPolling() {
      clearInterval(this.statusPoller);
      this.statusPoller = null;
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
          this.showError("An error occurred while tearing down resources.");
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
      this.creationStep = null;
      this.clusterPlanMessage = "Starting cluster setup...";
      this.clusterPlanRunningDialog = true;
      const createPromise = MagicCastleRepository.create(this.magicCastle);
      createPromise.catch(() => {});
      try {
        await Promise.race([createPromise, this.sleep(PLAN_START_TIMEOUT_MS)]);
        isCommited = true;
        showPlan = "1";
      } catch (error) {
        if (error.response) {
          this.showError(error.response.data.message);
          isCommited = true;
        } else if (error.request) {
          console.log(error.request);
          // The request may have been accepted but the response timed out.
          isCommited = true;
          showPlan = "1";
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
      if (this.magicCastle.undeployed) {
        try {
          await MagicCastleRepository.update(this.hostname, this.magicCastle);
          this.$disableUnloadConfirmation();
          this.startStatusPolling();
        } catch (e) {
          this.showError(e.response?.data?.message || e.message);
        }
        return;
      }
      let planCreator = async () => MagicCastleRepository.update(this.hostname, this.magicCastle);
      await this.showPlanConfirmationDialog({ planCreator });
    },
    async rebuildCluster() {
      if (this.status === ClusterStatusCode.CREATED) {
        await this.showPlanConfirmationDialog();
        return;
      }
      const planCreator = async () => MagicCastleRepository.rebuild(this.hostname);
      await this.showPlanConfirmationDialog({ planCreator });
    },
    async planDestruction() {
      let planCreator = async () => MagicCastleRepository.teardown(this.hostname);
      await this.showPlanConfirmationDialog({ planCreator, destroy: true });
    },
    async discardTeardown() {
      this.stopStatusPolling();
      this.loading = true;
      try {
        await MagicCastleRepository.discardTeardown(this.hostname);
        this.resourcesChanges = [];
        await this.goToClustersList();
      } catch (e) {
        this.showError(e.response?.data?.message || e.message);
        this.clusterDestructionDialog = true;
      } finally {
        this.loading = false;
      }
    },
    async forceDestruction() {
      try {
        this.unloadCluster();
        await MagicCastleRepository.delete(this.hostname);
        this.goHome();
      } catch (e) {
        this.showError(e.response.data.message);
      }
    },
    async applyCluster() {
      this.applyRequested = true;
      try {
        await MagicCastleRepository.apply(this.hostname);
        this.startStatusPolling();
      } catch (e) {
        this.applyRequested = false;
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
      this.creationStep = null;
      const hostname = this.getClusterHostname();
      try {
        // Create plan
        this.clusterPlanRunningDialog = true;
        const planPromise = options.planCreator();
        planPromise.catch(() => {});
        try {
          await Promise.race([planPromise, this.sleep(PLAN_START_TIMEOUT_MS)]);
        } catch (e) {
          if (e.response) {
            throw e;
          }
          if (!e.request) {
            throw e;
          }
          // If the request timed out, keep going and poll for plan status.
        }

        // Fetch plan
        const { status, message, progress } = await this.waitForPlanCompletion(hostname);
        if ([ClusterStatusCode.PLAN_ERROR, ClusterStatusCode.DESTROY_ERROR].includes(status)) {
          this.showError(message || "An error occurred while generating the plan.");
          this.clusterPlanRunningDialog = false;
          return;
        }
        if (status === ClusterStatusCode.NOT_DEPLOYED) {
          this.clusterPlanRunningDialog = false;
          this.goHome();
          return;
        }
        this.resourcesChanges =
          (progress || []).filter((resource) => !isEqual(resource.change.actions, ["no-op"])) || [];
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
        if (e.response) {
          this.showError(e.response.data.message);
        } else if (e.request) {
          this.showError("Plan creation request was made but no response was received.");
        } else if (e.message) {
          this.showError(e.message);
        } else {
          this.showError("Plan creation request setting up triggered an error.");
        }
      }
    },
    getClusterHostname() {
      if (this.hostname) {
        return this.hostname;
      }
      if (!this.magicCastle) {
        return null;
      }
      return `${this.magicCastle.cluster_name}.${this.magicCastle.domain}`;
    },
    async waitForPlanCompletion(hostname) {
      if (!hostname) {
        throw new Error("Cluster hostname is missing.");
      }
      const start = Date.now();
      for (;;) {
        const { status, message, progress, creation_step } = (await MagicCastleRepository.getStatus(hostname)).data;
        this.creationStep = creation_step || null;
        this.clusterPlanMessage =
          status === ClusterStatusCode.NOT_FOUND
            ? "Waiting for cluster setup to start..."
            : "Generating resource plan... please wait.";
        if (
          [
            ClusterStatusCode.CREATED,
            ClusterStatusCode.PLAN_ERROR,
            ClusterStatusCode.DESTROY_ERROR,
            ClusterStatusCode.NOT_DEPLOYED,
          ].includes(status)
        ) {
          return { status, message, progress };
        }
        if (Date.now() - start > MAX_PLAN_WAIT_MS) {
          throw new Error("Plan generation is taking too long. Please try again later.");
        }
        await this.sleep(POLL_STATUS_INTERVAL);
      }
    },
    sleep(ms) {
      return new Promise((resolve) => setTimeout(resolve, ms));
    },
    unloadCluster() {
      this.applyRequested = false;
      this.magicCastle = null;
      this.status = null;
    },
  },
};
</script>
