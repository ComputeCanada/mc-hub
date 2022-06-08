<template>
  <v-container>
    <v-card :max-width="600" class="mx-auto">
      <v-data-table :headers="headers" :items="projects">
        <template #top>
          <v-toolbar flat>
            <v-toolbar-title>Your Projects</v-toolbar-title>
            <v-divider vertical class="mx-4" inset />
            <v-spacer />
            <cloud-provider-input @newProject="updateProjects" />
          </v-toolbar>
        </template>
        <template v-slot:[`item.actions`]="{ item }">
          <v-icon @click="deleteItem(item)" :disabled="item.nb_clusters > 0"> mdi-delete </v-icon>
        </template>
      </v-data-table>
    </v-card>
  </v-container>
</template>

<script>
import ProjectRepository from "@/repositories/ProjectRepository";
import CloudProviderInput from "@/components/ui/CloudProviderInput";

export default {
  name: "Projects",
  components: {
    CloudProviderInput,
  },
  data() {
    return {
      projects: [],
      headers: [
        { text: "Name", value: "name" },
        { text: "Provider", value: "provider" },
        { text: "# Clusters", value: "nb_clusters" },
        { text: "Remove?", value: "actions", sortable: false },
      ],
    };
  },
  created() {
    this.updateProjects();
  },
  methods: {
    async updateProjects() {
      this.projects = (await ProjectRepository.getAll()).data;
    },
    deleteItem(item) {
      ProjectRepository.delete(item.id).then(this.updateProjects);
    },
  },
};
</script>
