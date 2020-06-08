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
        </template>
      </v-data-table>
    </v-card>
  </v-container>
</template>

<script>
import MagicCastleRepository from "@/repositories/MagicCastleRepository";
import StatusChip from "@/components/StatusChip";
export default {
  name: "ClustersList",
  components: { StatusChip },
  data() {
    return {
      loading: true,
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
  async created() {
    this.magicCastles = (await MagicCastleRepository.getAll()).data;
    this.loading = false;
  }
};
</script>

<style scoped></style>
