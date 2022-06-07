<template>
  <v-container>
    <v-card :max-width="600" class="mx-auto">
      <v-data-table :headers="headers" :items="projects">
        <template #top>
          <v-toolbar flat>
            <v-toolbar-title>Your Projects</v-toolbar-title>
            <v-divider vertical class="mx-4" inset />
            <v-spacer />
            <v-dialog v-model="dialog" max-width="500px">
              <template v-slot:activator="{ on, attrs }">
                <v-btn color="primary" dark class="mb-2" v-bind="attrs" v-on="on"> Add Project </v-btn>
              </template>
              <v-card>
                <v-card-title>
                  <span class="text-h5">Add Project</span>
                </v-card-title>
                <v-card-text>
                  <v-container>
                    <v-list>
                      <v-list-item>
                        <v-select :items="providers" v-model="newProject.provider" label="Cloud provider"></v-select>
                      </v-list-item>
                      <v-list-item>
                        <v-text-field v-model="newProject.name" label="Project name"></v-text-field>
                      </v-list-item>
                      <v-list-item>
                        <v-text-field v-model="newProject.env.OS_AUTH_URL" label="OS_AUTH_URL"></v-text-field>
                      </v-list-item>
                      <v-list-item>
                        <v-text-field
                          v-model="newProject.env.OS_APPLICATION_CREDENTIAL_ID"
                          label="OS_APP_CREDENTIAL_ID"
                        ></v-text-field>
                      </v-list-item>
                      <v-list-item>
                        <v-text-field
                          v-model="newProject.env.OS_APPLICATION_CREDENTIAL_SECRET"
                          label="OS_APP_CREDENTIAL_SECRET"
                        ></v-text-field>
                      </v-list-item>
                    </v-list>
                  </v-container>
                </v-card-text>
                <v-card-actions>
                  <v-spacer></v-spacer>
                  <v-btn color="blue darken-1" text @click="close"> Cancel </v-btn>
                  <v-btn color="blue darken-1" text @click="add"> Add </v-btn>
                </v-card-actions>
              </v-card>
            </v-dialog>
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

export default {
  data() {
    return {
      dialog: false,
      projects: [],
      providers: ["openstack"],
      headers: [
        { text: "Name", value: "name" },
        { text: "Provider", value: "provider" },
        { text: "# Clusters", value: "nb_clusters" },
        { text: "Remove?", value: "actions", sortable: false },
      ],
      defaultProject: {
        name: "",
        provider: "openstack",
        env: {
          OS_AUTH_URL: "",
          OS_APPLICATION_CREDENTIAL_ID: "",
          OS_APPLICATION_CREDENTIAL_SECRET: "",
        },
      },
      newProject: {
        name: "",
        provider: "openstack",
        env: {
          OS_AUTH_URL: "",
          OS_APPLICATION_CREDENTIAL_ID: "",
          OS_APPLICATION_CREDENTIAL_SECRET: "",
        },
      },
    };
  },
  watch: {
    dialog(val) {
      val || this.close();
    },
  },
  async created() {
    this.projects = (await ProjectRepository.getAll()).data;
  },
  methods: {
    deleteItem(item) {
      ProjectRepository.delete(item.id).then(() => {
        this.projects = this.projects.filter((i) => i.id !== item.id);
      });
    },
    async add() {
      const project = (await ProjectRepository.post(this.newProject)).data;
      this.projects.push(project);
      this.newProject = Object.assign({}, this.defaultProject);
      this.close();
    },
    close() {
      this.dialog = false;
      this.$nextTick(() => {
        this.newProject = Object.assign({}, this.defaultProject);
      });
    },
  },
};
</script>
