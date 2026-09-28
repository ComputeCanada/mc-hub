<template>
  <v-container>
    <v-card :max-width="800" class="mx-auto">
      <v-alert v-if="error" type="error">{{ error }}</v-alert>
      <v-data-table :headers="headers" :items="projects" item-value="id">
        <template #top>
          <v-toolbar flat>
            <v-toolbar-title>Your Projects</v-toolbar-title>
            <v-divider vertical class="mx-4" inset />
            <v-spacer />
            <cloud-provider-input @newProject="updateProjectList" />
          </v-toolbar>
        </template>
        <template v-slot:[`item.default`]="{ item }">
          <!-- Keep the confirmed selection while the preference is being saved. -->
          <v-checkbox-btn
            :model-value="item.id === defaultProjectId"
            :disabled="savingDefault !== null"
            :aria-label="'Set ' + item.name + ' as default project'"
            @click.prevent="setDefaultProject(item)"
            @keydown.space.prevent="setDefaultProject(item)"
            @keydown.enter.prevent="setDefaultProject(item)"
          />
        </template>
        <template v-slot:[`item.actions`]="{ item }">
          <div class="d-flex flex-nowrap align-center justify-end text-no-wrap">
            <project-editor :id="item.id" :admin="item.admin" @saved="updateProjectList" />
            <project-membership :id="item.id" :admin="item.admin" @saved="updateProjectList" />
            <project-notifications v-if="item.can_manage_notifications" :id="item.id" />
            <v-btn
              color="secondary"
              variant="text"
              :aria-label="'Delete ' + item.name"
              v-if="item.admin"
              @click="deleteItem(item)"
              :disabled="item.nb_clusters > 0"
            >
              <v-icon>mdi-delete</v-icon>
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
import ProjectNotifications from "@/components/ui/ProjectNotifications";
import ProjectMembership from "@/components/ui/ProjectMembership";

export default {
  name: "Projects",
  components: {
    ProjectNotifications,
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
        { title: "Default", key: "default", sortable: false, align: "center" },
        { title: "Name", key: "name" },
        { title: "Provider", key: "provider" },
        { title: "# Clusters", key: "nb_clusters", align: "end" },
        { title: "", key: "actions", sortable: false, width: "1%" },
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
    async deleteItem(item) {
      if (!item.admin || item.nb_clusters > 0) return;
      try {
        await ProjectRepository.delete(item.id);
        await this.updateProjectList();
      } catch (error) {
        this.error = error.response?.data?.message || "Unable to delete the project. Please try again.";
      }
    },
  },
};
</script>
