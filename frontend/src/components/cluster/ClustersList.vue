<template>
  <v-container>
    <v-card :max-width="800" class="mx-auto">
      <v-data-table :headers="headers" :items="magicCastles" :loading="loading">
        <template #top>
          <v-toolbar flat>
            <v-toolbar-title>Your Magic Castles</v-toolbar-title>
            <v-divider vertical class="mx-4" inset />
            <v-spacer />
            <v-btn color="primary" big to="/create-cluster">Create cluster</v-btn>
          </v-toolbar>
        </template>
        <template #item.name="{item}"
          ><router-link :to="`/clusters/${item.name}`">{{ item.name }}</router-link></template
        >
        <template #item.status="{item}"><status-chip :status="item.status"/></template>
        <template #item.actions="{item}">
          <v-btn icon :to="`/clusters/${item.name}`"><v-icon>mdi-pencil</v-icon></v-btn>
          <v-btn icon @click="showClusterDestructionDialog(item.name)"><v-icon>mdi-delete</v-icon></v-btn>
        </template>
      </v-data-table>
    </v-card>
    <message-dialog v-model="errorDialog" type="error">
      {{ errorMessage }}
    </message-dialog>
    <confirm-dialog
      alert
      encourage-cancel
      title="Destruction confirmation"
      v-model="clusterDestructionDialog"
      @confirm="destroyCluster"
    >
      Are you sure you want to permanently destroy this cluster and all its data?
    </confirm-dialog>
  </v-container>
</template>

<script>
import MagicCastleRepository from "@/repositories/MagicCastleRepository";
import StatusChip from "@/components/ui/StatusChip";
import ConfirmDialog from "@/components/ui/ConfirmDialog";
import MessageDialog from "@/components/ui/MessageDialog";

const POLL_STATUS_INTERVAL = 5000;

export default {
  name: "ClustersList",
  components: { StatusChip, ConfirmDialog, MessageDialog },
  data() {
    return {
      loading: true,
      clusterDestructionDialog: false,
      currentClusterName: null,
      errorDialog: false,
      statusPoller: null,

      headers: [
        {
          text: "Name",
          value: "name"
        },
        {
          text: "Status",
          value: "status"
        },
        {
          text: "Actions",
          value: "actions",
          sortable: false,
          align: "right"
        }
      ],
      magicCastles: []
    };
  },
  created() {
    this.startStatusPolling();
  },
  beforeDestroy() {
    this.stopStatusPolling();
  },
  methods: {
    startStatusPolling() {
      let fetchStatus = () => {
        this.loadMagicCastlesStatus();
      };
      this.statusPoller = setInterval(fetchStatus, POLL_STATUS_INTERVAL);
      fetchStatus();
    },
    stopStatusPolling() {
      clearInterval(this.statusPoller);
    },
    async loadMagicCastlesStatus() {
      this.loading = true;
      this.magicCastles = (await MagicCastleRepository.getAll()).data;
      this.loading = false;
    },
    showError(message) {
      this.errorDialog = true;
      this.errorMessage = message;
    },
    showClusterDestructionDialog(clusterName) {
      this.clusterDestructionDialog = true;
      this.currentClusterName = clusterName;
    },
    async destroyCluster() {
      try {
        await MagicCastleRepository.delete(this.currentClusterName);
        await this.loadMagicCastlesStatus();
      } catch (e) {
        this.showError(e.response.data.message);
      }
    }
  }
};
</script>

<style scoped></style>
