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
            <cloud-provider-input @newProject="updateProjectList" />
          </v-toolbar>
        </template>
        <template v-slot:[`item.default`]="{ item }">
          <v-simple-checkbox
            role="checkbox"
            :tabindex="savingDefault !== null ? -1 : 0"
            :aria-checked="item.id === defaultProjectId ? 'true' : 'false'"
            :value="item.id === defaultProjectId"
            :disabled="savingDefault !== null"
            :aria-label="'Set ' + item.name + ' as default project'"
            @input="setDefaultProject(item)"
            @keydown.space.prevent="setDefaultProject(item)"
            @keydown.enter.prevent="setDefaultProject(item)"
          />
        </template>
        <template v-slot:[`item.actions`]="{ item }">
          <div class="d-flex flex-nowrap align-center justify-end text-no-wrap">
            <project-editor :id="item.id" :admin="item.admin" />
            <project-membership :id="item.id" :admin="item.admin" @saved="updateProjectList" />
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
import ProjectEditor from "@/components/ui/ProjectEditor";
import ProjectMembership from "@/components/ui/ProjectMembership";

export default {
  name: "Projects",
  components: {
    CloudProviderInput,
    ProjectMembership,
    ProjectEditor,
  },
  data() {
    return {
      projects: [],
      defaultProjectId: null,
      savingDefault: null,
      error: "",
      headers: [
        { text: "Default", value: "default", sortable: false, align: "center" },
        { text: "Name", value: "name" },
        { text: "Provider", value: "provider" },
        { text: "# Clusters", value: "nb_clusters", align: "right" },
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
        this.defaultProjectId = user.data.default_project_id;
        this.error = "";
      } catch (error) {
        this.error = error.response?.data?.message || "Unable to load projects. Please try again.";
      }
    },
    async setDefaultProject(item) {
      if (item.id === this.defaultProjectId || this.savingDefault !== null) return;
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
