<template>
  <v-container>
    <v-card :max-width="800" class="mx-auto">
      <v-alert v-if="error" type="error">{{ error }}</v-alert>
      <v-data-table :headers="headers" :items="projects">
        <template #top>
          <v-toolbar flat>
            <v-toolbar-title>Your Projects</v-toolbar-title>
            <v-divider vertical class="mx-4" inset />
            <v-spacer />
            <cloud-provider-input :hub-admin="hubAdmin" @newProject="updateProjectList" />
          </v-toolbar>
        </template>
        <template v-slot:[`item.name`]="{ item }">
          {{ item.name }}
          <v-chip v-if="item.id === defaultProjectId" small class="ml-2" color="primary">Default</v-chip>
        </template>
        <template v-slot:[`item.actions`]="{ item }">
          <div class="d-flex flex-nowrap align-center justify-end text-no-wrap">
            <v-btn
              v-if="item.id !== defaultProjectId"
              text
              :disabled="savingDefault !== null"
              :loading="savingDefault === item.id"
              @click="setDefaultProject(item)"
              >Default</v-btn
            >
            <project-membership :id="item.id" :admin="item.admin" :hub-admin="hubAdmin" />
            <v-btn color="secondary" text v-if="item.admin" @click="deleteItem(item)" :disabled="item.nb_clusters > 0">
              <v-icon> mdi-delete </v-icon>
              delete
            </v-btn>
            <div v-else>not owner</div>
          </div>
        </template>
      </v-data-table>
    </v-card>
  </v-container>
</template>

<script>
import ProjectRepository from "@/repositories/ProjectRepository";
import UserRepository from "@/repositories/UserRepository";
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
      hubAdmin: false,
      defaultProjectId: null,
      savingDefault: null,
      error: "",
      headers: [
        { text: "Name", value: "name" },
        { text: "Provider", value: "provider" },
        { text: "# Clusters", value: "nb_clusters" },
        { text: "", value: "actions", sortable: false, width: "1%" },
      ],
    };
  },
  async created() {
    await this.updateProjectList();
  },
  methods: {
    async updateProjectList() {
      try {
        const [projects, user] = await Promise.all([ProjectRepository.getAll(), UserRepository.getCurrent()]);
        this.projects = projects.data;
        this.hubAdmin = user.data.is_admin === true;
        this.defaultProjectId = user.data.default_project_id;
        this.error = "";
      } catch (error) {
        this.error = error.response?.data?.message || "Unable to load projects. Please try again.";
      }
    },
    async setDefaultProject(item) {
      this.savingDefault = item.id;
      this.error = "";
      try {
        const { data } = await UserRepository.setDefaultProject(item.id);
        this.defaultProjectId = data.default_project_id;
      } catch (error) {
        this.error = error.response?.data?.message || "Unable to save your default project. Please try again.";
      } finally {
        this.savingDefault = null;
      }
    },
    deleteItem(item) {
      ProjectRepository.delete(item.id).then(this.updateProjectList);
    },
  },
};
</script>
