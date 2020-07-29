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
        <template #item.cluster_name="{item}">
          <router-link :to="`/clusters/${item.hostname}`">{{ item.cluster_name }}</router-link>
        </template>
        <template #item.status="{item}">
          <status-chip :status="item.status" />
        </template>
        <template #item.actions="{item}">
          <v-btn icon :to="`/clusters/${item.hostname}`">
            <v-icon>mdi-pencil</v-icon>
          </v-btn>
          <v-btn icon @click="destroyCluster(item.hostname)">
            <v-icon>mdi-delete</v-icon>
          </v-btn>
        </template>
      </v-data-table>
    </v-card>
  </v-container>
</template>

<script>
import MagicCastleRepository from "@/repositories/MagicCastleRepository";
import StatusChip from "@/components/ui/StatusChip";

const POLL_STATUS_INTERVAL = 5000;

export default {
  name: "ClustersList",
  components: { StatusChip },
  data() {
    return {
      loading: true,
      currentHostname: null,
      statusPoller: null,

      magicCastles: []
    };
  },
  created() {
    this.startStatusPolling();
  },
  beforeDestroy() {
    this.stopStatusPolling();
  },
  computed: {
    headers() {
      if (this.magicCastles.some(magicCastle => "owner" in magicCastle)) {
        return [
          {
            text: "Cluster name",
            value: "cluster_name"
          },
          {
            text: "Domain",
            value: "domain"
          },
          {
            text: "Status",
            value: "status"
          },
          {
            text: "Owner",
            value: "owner"
          },
          {
            text: "Actions",
            value: "actions",
            sortable: false,
            align: "right"
          }
        ];
      } else {
        return [
          {
            text: "Cluster name",
            value: "cluster_name"
          },
          {
            text: "Domain",
            value: "domain"
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
        ];
      }
    }
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
    async destroyCluster(hostname) {
      await this.$router.push({
        path: `/clusters/${hostname}`,
        query: { destroy: "1" }
      });
    }
  }
};
</script>

<style scoped></style>
