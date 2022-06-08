<template>
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
            <v-list>
              <v-list-item>
                <v-select :items="providers" v-model="newProject.provider" label="Cloud provider"></v-select>
              </v-list-item>
              <v-list-item>
                <v-text-field v-model="newProject.name" label="Project name"></v-text-field>
              </v-list-item>
            </v-list>
            <div v-for="env_var in provider_var[newProject.provider]" :key="env_var">
              <v-list-item>
                <v-text-field v-model="newProject.env[env_var]" :label="env_var"></v-text-field>
              </v-list-item>
            </div>
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
</template>

<script>
import ProjectRepository from "@/repositories/ProjectRepository";

export default {
  name: "CloudProviderInput",
  emits: ["newProject"],
  data() {
    return {
      dialog: false,
      providers: ["openstack", "aws"],
      provider_var: {
        openstack: ["OS_AUTH_URL", "OS_APPLICATION_CREDENTIAL_ID", "OS_APPLICATION_CREDENTIAL_SECRET"],
        aws: ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"],
      },
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
  methods: {
    async add() {
      await ProjectRepository.post(this.newProject);
      this.$emit("newProject");
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
