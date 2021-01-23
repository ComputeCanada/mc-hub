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
        <template #item.status="{item}">
          <status-chip :status="item.status" />
        </template>
        <template #expanded-item="{headers, item}">
          <td :colspan="headers.length" :key="item.hostname">
            <v-container>
              <v-row class="pa-3">
                <h2>Cluster overview</h2>
              </v-row>
              <v-row>
                <v-col>Hostname</v-col>
                <v-col
                  ><code>{{ item.hostname }}</code></v-col
                >
              </v-row>
              <v-row>
                <v-col>Sudoer username</v-col>
                <v-col><code>centos</code></v-col>
              </v-row>
              <v-row>
                <v-col>FreeIPA admin username</v-col>
                <v-col><code>admin</code></v-col>
              </v-row>
              <v-row>
                <v-col>FreeIPA admin password</v-col>
                <v-col>
                  <password-display v-if="item.freeipa_passwd" :password="item.freeipa_passwd"></password-display>
                  <span v-else>not available</span>
                </v-col>
              </v-row>
              <v-row>
                <v-col>Guest usernames</v-col>
                <v-col
                  ><template v-if="item.nb_users">
                    <code>{{ getFirstUserName(item.nb_users) }}</code> -
                    <code>{{ getLastUserName(item.nb_users) }}</code>
                  </template>
                  <span v-else>not available</span>
                </v-col>
              </v-row>
              <v-row>
                <v-col>Guest password</v-col>
                <v-col>
                  <password-display v-if="item.guest_passwd" :password="item.guest_passwd" />
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
                <v-btn color="secondary" text :to="`/clusters/${item.hostname}`">
                  <v-icon class="mr-2">mdi-pencil</v-icon>
                  Edit
                </v-btn>
                <v-btn color="secondary" text @click="destroyCluster(item.hostname)">
                  <v-icon class="mr-2">mdi-delete</v-icon>
                  Delete
                </v-btn>
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

const POLL_STATUS_INTERVAL = 5000;

export default {
  name: "ClustersList",
  components: { StatusChip, PasswordDisplay },
  data() {
    return {
      currentHostname: null,
      statusPoller: null,
      loading: true,
      expandedRows: [],

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
            text: "",
            value: "data-table-expand"
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
            text: "",
            value: "data-table-expand"
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
      this.magicCastles = (await MagicCastleRepository.getAll()).data;
      this.loading = false;
    },
    async destroyCluster(hostname) {
      await this.$router.push({
        path: `/clusters/${hostname}`,
        query: { destroy: "1" }
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
    }
  }
};
</script>

<style scoped>
.v-data-table >>> table tbody tr:not(.v-data-table__expanded__content):not(.v-data-table__empty-wrapper) {
  cursor: pointer;
}
</style>
