<template>
  <v-container>
    <v-card :max-width="800" class="mx-auto">
      <v-data-table
        :headers="headers"
        :items="magicCastles"
        :loading="loading"
        show-expand
        single-expand
        item-key="hostname"
        :expanded.sync="expandedRows"
        @click:row="rowClicked"
      >
        <template #top>
          <v-toolbar flat>
            <v-toolbar-title>Your Magic Castles</v-toolbar-title>
            <v-divider vertical class="mx-4" inset />
            <v-spacer />
            <v-btn color="primary" big to="/create-cluster">Create cluster</v-btn>
          </v-toolbar>
        </template>
        <template v-slot:[`item.status`]="{ item }">
          <status-chip :status="item.status" />
        </template>
        <template #expanded-item="{ headers, item }">
          <td :colspan="headers.length" :key="item.hostname">
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
                <v-col>Sudoer username</v-col>
                <v-col>
                  <copy-button :color="expandedContentColor" text="centos" />
                  <code>centos</code></v-col
                >
              </v-row>
              <v-row>
                <v-col>FreeIPA admin username</v-col>
                <v-col>
                  <copy-button :color="expandedContentColor" text="admin" />
                  <code>admin</code></v-col
                >
              </v-row>
              <v-row>
                <v-col>FreeIPA admin password</v-col>
                <v-col>
                  <template v-if="item.freeipa_passwd">
                    <copy-button :color="expandedContentColor" :text="item.freeipa_passwd" />
                    <password-display :password="item.freeipa_passwd" :color="expandedContentColor" />
                  </template>
                  <span v-else>not available</span>
                </v-col>
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
                  color="primary"
                  :disabled="item.status !== 'provisioning_success'"
                  text
                  :href="`https://jupyter.${item.hostname}`"
                  target="_blank"
                  >JupyterHub
                </v-btn>
                <v-btn
                  color="primary"
                  :disabled="item.status !== 'provisioning_success'"
                  text
                  :href="`https://ipa.${item.hostname}`"
                  target="_blank"
                  >FreeIPA
                </v-btn>
                <v-btn
                  color="primary"
                  :disabled="item.status !== 'provisioning_success'"
                  text
                  :href="`https://mokey.${item.hostname}`"
                  target="_blank"
                  >Mokey
                </v-btn>
                <v-spacer />
                <v-btn
                  v-if="['build_running', 'destroy_running'].includes(item.status)"
                  color="secondary"
                  text
                  :to="`/clusters/${item.hostname}`"
                >
                  <v-icon class="mr-2">mdi-list-status</v-icon>
                  Check progress
                </v-btn>
                <div v-else>
                  <v-btn color="secondary" text :to="`/clusters/${item.hostname}`">
                    <v-icon class="mr-2">mdi-pencil</v-icon>
                    Edit
                  </v-btn>
                  <v-btn color="secondary" text @click="destroyCluster(item.hostname)">
                    <v-icon class="mr-2">mdi-delete</v-icon>
                    Delete
                  </v-btn>
                </div>
              </v-row>
            </v-container>
          </td>
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

const POLL_STATUS_INTERVAL = 5000;

export default {
  name: "ClustersList",
  components: { CopyButton, StatusChip, PasswordDisplay },
  data() {
    return {
      currentHostname: null,
      statusPoller: null,
      loading: true,
      expandedRows: [],
      expandedContentColor: "#C0341D",
      mcStatusPromise: null,
      magicCastles: [],
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
      let base_headers = [
        {
          text: "Cluster name",
          value: "cluster_name",
        },
        {
          text: "Domain",
          value: "domain",
        },
        {
          text: "Project",
          value: "cloud_id",
        },
        {
          text: "Age",
          value: "age",
        },
        {
          text: "Status",
          value: "status",
        },
      ];
      let end_headers = [
        {
          text: "",
          value: "data-table-expand",
        },
      ];
      if (this.magicCastles.some((magicCastle) => "owner" in magicCastle && magicCastle.owner != null)) {
        return base_headers.concat([{ text: "Owner", value: "owner" }], end_headers);
      } else {
        return base_headers.concat(end_headers);
      }
    },
  },
  methods: {
    startStatusPolling() {
      const fetchStatus = () => {
        this.loadMagicCastlesStatus();
      };
      this.statusPoller = setInterval(fetchStatus, POLL_STATUS_INTERVAL);
      fetchStatus();
    },
    stopStatusPolling() {
      clearInterval(this.statusPoller);
    },
    async loadMagicCastlesStatus() {
      if (this.mcStatusPromise === null) {
        this.mcStatusPromise = MagicCastleRepository.getAll();
        this.magicCastles = (await this.mcStatusPromise).data;
        this.loading = false;
        this.mcStatusPromise = null;
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
    rowClicked(item) {
      const expandedRowIndex = this.expandedRows.indexOf(item);
      this.expandedRows = [];
      if (expandedRowIndex === -1) {
        this.expandedRows.push(item);
      }
    },
  },
};
</script>

<style scoped>
.v-data-table >>> table tbody tr:not(.v-data-table__expanded__content):not(.v-data-table__empty-wrapper) {
  cursor: pointer;
}
</style>
