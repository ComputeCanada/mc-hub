<template>
  <v-container>
    <v-card :max-width="800" class="mx-auto">
      <v-alert v-if="error" type="error">{{ error }}</v-alert>
      <v-data-table
        :headers="headers"
        :items="magicCastles"
        :loading="loading"
        show-expand
        item-value="hostname"
        :expanded="expandedRows"
        @update:expanded="expandedRows = $event.slice(-1)"
        @click:row="rowClicked"
      >
        <template #top>
          <v-toolbar flat>
            <v-toolbar-title>Your Magic Castles</v-toolbar-title>
            <v-divider vertical class="mx-4" inset />
            <v-spacer />
            <v-btn color="primary" to="/create-cluster">Create cluster</v-btn>
          </v-toolbar>
        </template>
        <template v-slot:[`item.status`]="{ item }">
          <status-chip :status="item.status" :health="item.health" :undeployed="item.undeployed" />
        </template>
        <template v-slot:[`item.owner`]="{ item }">
          {{ item.owner ? item.owner.split("@")[0] : "Not set" }}
        </template>
        <template #expanded-row="{ columns, item }">
          <tr class="cluster-overview">
            <td :colspan="columns.length">
              <v-container>
                <v-row class="pa-3">
                  <h2>Cluster overview</h2>
                </v-row>
                <v-row>
                  <v-col>Hostname</v-col>
                  <v-col>
                    <copy-button :color="expandedContentColor" :text="item.hostname" />
                    <code>{{ item.hostname }}</code></v-col
                  >
                </v-row>
                <v-row>
                  <v-col>Expiration date</v-col>
                  <v-col>{{ item.expiration_date || "Not set" }}</v-col>
                </v-row>
                <v-row>
                  <v-col>Sudoer username</v-col>
                  <v-col>
                    <copy-button :color="expandedContentColor" text="centos" />
                    <code>centos</code></v-col
                  >
                </v-row>
                <v-row>
                  <v-col>Guest usernames</v-col>
                  <v-col>
                    <template v-if="item.nb_users">
                      <code>{{ getFirstUserName(item.nb_users) }}</code> -
                      <code>{{ getLastUserName(item.nb_users) }}</code>
                    </template>
                    <span v-else>not available</span>
                  </v-col>
                </v-row>
                <v-row>
                  <v-col>Guest password</v-col>
                  <v-col>
                    <template v-if="item.guest_passwd">
                      <copy-button :color="expandedContentColor" :text="item.guest_passwd" />
                      <password-display :password="item.guest_passwd" :color="expandedContentColor" />
                    </template>
                    <span v-else>not available</span></v-col
                  >
                </v-row>
                <v-divider class="mt-4" />
                <v-row class="pa-2">
                  <v-btn
                    v-for="(service, serviceName) in item.services"
                    :key="serviceName"
                    color="primary"
                    :disabled="item.status !== 'provisioning_success'"
                    variant="text"
                    :href="service.url"
                    target="_blank"
                  >
                    <v-icon
                      size="x-small"
                      class="mr-2"
                      :color="serviceStatusColor(service)"
                      :aria-label="serviceStatusLabel(service)"
                      :title="serviceStatusLabel(service)"
                      role="img"
                      >mdi-circle</v-icon
                    >
                    {{ service.label }}
                  </v-btn>
                  <v-spacer />
                  <v-btn
                    v-if="['build_running', 'destroy_running', 'plan_running'].includes(item.status)"
                    color="secondary"
                    variant="text"
                    :to="`/clusters/${item.hostname}`"
                  >
                    <v-icon class="mr-2">mdi-list-status</v-icon>
                    Check progress
                  </v-btn>
                  <div v-else>
                    <v-btn
                      v-if="['build_error', 'destroy_error', 'plan_error'].includes(item.status)"
                      color="error"
                      variant="text"
                      :to="`/clusters/${item.hostname}`"
                      >View failure details</v-btn
                    >
                    <v-btn color="secondary" variant="text" :to="`/clusters/${item.hostname}`">
                      <v-icon class="mr-2">mdi-pencil</v-icon>
                      Edit
                    </v-btn>
                    <v-btn color="secondary" variant="text" @click="destroyCluster(item.hostname)">
                      <v-icon class="mr-2">mdi-delete</v-icon>
                      {{
                        canDestroyCluster(item)
                          ? "Delete"
                          : item.status === "destroy_error"
                          ? "Retry teardown"
                          : "Tear down"
                      }}
                    </v-btn>
                  </div>
                </v-row>
              </v-container>
            </td>
          </tr>
        </template>
      </v-data-table>
    </v-card>
  </v-container>
</template>

<script>
import MagicCastleRepository from "@/repositories/MagicCastleRepository";
import StatusChip from "@/components/ui/StatusChip";
import PasswordDisplay from "@/components/ui/PasswordDisplay.vue";
import CopyButton from "@/components/ui/CopyButton";
import { canDestroyCluster } from "@/models/ClusterStatusCode";

const POLL_STATUS_INTERVAL = 5000;

export default {
  name: "ClustersList",
  components: { CopyButton, StatusChip, PasswordDisplay },
  data() {
    return {
      currentHostname: null,
      statusPoller: null,
      loading: true,
      disposed: false,
      error: "",
      expandedRows: [],
      expandedContentColor: "#C0341D",
      mcStatusPromise: null,
      magicCastles: [],
    };
  },
  created() {
    this.startStatusPolling();
  },
  beforeUnmount() {
    this.disposed = true;
    this.stopStatusPolling();
  },
  computed: {
    headers() {
      return [
        {
          title: "Cluster name",
          key: "cluster_name",
        },
        {
          title: "Domain",
          key: "domain",
        },
        {
          title: "Project",
          key: "cloud.name",
        },
        {
          title: "Owner",
          key: "owner",
        },
        {
          title: "Age",
          key: "age",
        },
        {
          title: "Status",
          key: "status",
        },
        {
          title: "",
          key: "data-table-expand",
        },
      ];
    },
  },
  methods: {
    canDestroyCluster,
    serviceStatusColor(service) {
      return service.status === "healthy" ? "green" : "red";
    },
    serviceStatusLabel(service) {
      const availability = service.status === "healthy" ? "available" : "unhealthy";
      return `${service.label} is ${availability}`;
    },
    startStatusPolling() {
      if (this.disposed) return;
      this.stopStatusPolling();
      const fetchStatus = () => {
        this.loadMagicCastlesStatus();
      };
      this.statusPoller = setInterval(fetchStatus, POLL_STATUS_INTERVAL);
      fetchStatus();
    },
    stopStatusPolling() {
      clearInterval(this.statusPoller);
      this.statusPoller = null;
    },
    async loadMagicCastlesStatus() {
      if (this.disposed || this.mcStatusPromise !== null) return;
      this.mcStatusPromise = MagicCastleRepository.getAll();
      try {
        const { data } = await this.mcStatusPromise;
        if (this.disposed) return;
        this.magicCastles = data;
        this.expandedRows = this.expandedRows.filter((hostname) => data.some((item) => item.hostname === hostname));
        this.error = "";
      } catch (error) {
        if (!this.disposed)
          this.error = error.response?.data?.message || "Unable to load clusters. Retrying automatically.";
      } finally {
        if (!this.disposed) {
          this.loading = false;
          this.mcStatusPromise = null;
        }
      }
    },
    async destroyCluster(hostname) {
      await this.$router.push({
        path: `/clusters/${hostname}`,
        query: { destroy: "1" },
      });
    },
    getFirstUserName(nbUsers) {
      return "user" + "1".padStart(Math.floor(Math.log10(nbUsers)) + 1, "0");
    },
    getLastUserName(nbUsers) {
      return "user" + nbUsers;
    },
    rowClicked(event, { item }) {
      if (event.target.closest("button, a, input, [role='button']")) return;
      this.expandedRows = this.expandedRows.includes(item.hostname) ? [] : [item.hostname];
    },
  },
};
</script>

<style scoped>
.v-data-table :deep(tbody > tr.v-data-table__tr) {
  cursor: pointer;
}
</style>
