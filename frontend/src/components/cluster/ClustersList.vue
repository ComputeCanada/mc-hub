<template>
  <v-container>
    <v-card :max-width="800" class="mx-auto">
      <v-data-table :headers="headers" :items="magicCastles">
        <template #top>
          <v-toolbar flat>
            <v-toolbar-title>Your Magic Castles</v-toolbar-title>
            <v-divider vertical class="mx-4" inset />
            <v-spacer />
            <v-btn color="primary" big to="/create-cluster"
              >Create cluster</v-btn
            >
          </v-toolbar>
        </template>
        <template #item.status="{item}">
          <status-chip :status="item.status" />
        </template>
        <template #item.actions="{item}">
          <v-menu offset-y>
            <template #activator="{ on, attrs }">
              <v-btn
                :disabled="item.status != 'provisioning_success'"
                icon
                v-on="on"
                v-bind="attrs"
              >
                <v-icon>mdi-desktop-mac</v-icon>
              </v-btn>
            </template>
            <v-list>
              <v-list-item
                :href="`https://jupyter.${item.hostname}`"
                target="_blank"
              >
                JupyterHub
              </v-list-item>
              <v-list-item
                :href="`https://mokey.${item.hostname}`"
                target="_blank"
              >
                Mokey
              </v-list-item>
              <v-list-item
                :href="`https://ipa.${item.hostname}`"
                target="_blank"
              >
                FreeIPA
              </v-list-item>
            </v-list>
          </v-menu>
          <v-btn icon :to="`/clusters/${item.hostname}`">
            <v-icon
              v-if="['build_running', 'destroy_running'].includes(item.status)"
              >mdi-list-status</v-icon
            >
            <v-icon v-else>mdi-pencil</v-icon>
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
      this.magicCastles = (await MagicCastleRepository.getAll()).data;
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
