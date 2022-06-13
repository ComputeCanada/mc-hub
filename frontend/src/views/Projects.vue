<template>
  <v-container>
    <v-card :max-width="600" class="mx-auto">
      <v-data-table :headers="headers" :items="projects">
        <template #top>
          <v-toolbar flat>
            <v-toolbar-title>Your Projects</v-toolbar-title>
            <v-divider vertical class="mx-4" inset />
            <v-spacer />
            <cloud-provider-input @newProject="updateProjectList" />
          </v-toolbar>
        </template>
        <template v-slot:[`item.actions`]="{ item }">
          <project-membership :id="item.id" />
          <v-btn color="secondary" v-if="item.admin" @click="deleteItem(item)" :disabled="item.nb_clusters > 0">
            <v-icon> mdi-delete </v-icon>
          </v-btn>
          <div v-else>not owner</div>
        </template>
      </v-data-table>
    </v-card>
  </v-container>
</template>

<script>
import ProjectRepository from "@/repositories/ProjectRepository";
import CloudProviderInput from "@/components/ui/CloudProviderInput";
import ProjectMembership from "@/components/ui/ProjectMembership";

export default {
  name: "Projects",
  components: {
    CloudProviderInput,
    ProjectMembership,
  },
  data() {
    return {
      projects: [],
      headers: [
        { text: "Name", value: "name" },
        { text: "Provider", value: "provider" },
        { text: "# Clusters", value: "nb_clusters" },
        { text: "Edit / Delete", value: "actions", sortable: false },
      ],
    };
  },
  created() {
    this.updateProjectList();
  },
  methods: {
    async updateProjectList() {
      this.projects = (await ProjectRepository.getAll()).data;
    },
    deleteItem(item) {
      ProjectRepository.delete(item.id).then(this.updateProjectList);
    },
  },
};
</script>
