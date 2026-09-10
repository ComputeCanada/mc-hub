<template>
  <v-dialog v-model="dialog" max-width="500px">
    <template v-slot:activator="{ on, attrs }">
      <v-btn color="primary" dark class="mb-2" v-bind="attrs" v-on="on"> Add Project </v-btn>
    </template>
    <message-dialog v-model="errorDialog" type="error">{{ errorMessage }}</message-dialog>
    <v-card>
      <v-card-title>
        <span class="text-h5">Add Project</span>
      </v-card-title>
      <v-card-text>
        <v-container>
          <v-select :items="providers" v-model="newProject.provider" label="Cloud provider"></v-select>
          <v-text-field v-model="newProject.name" label="Project name"></v-text-field>
          <v-text-field
            v-model="newProject.agent_pool_name"
            label="Agent Pool Name (optional)"
            clearable
          ></v-text-field>
          <aws-credentials v-if="newProject.provider === 'aws'" v-model="newProject.env" />
          <div v-for="env_var in provider_var[newProject.provider]" :key="env_var">
            <v-text-field v-model="newProject.env[env_var]" :label="env_var"></v-text-field>
          </div>
          <open-stack-subnet v-if="newProject.provider === 'openstack'" v-model="newProject.env" />
        </v-container>
      </v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn color="blue darken-1" text @click="close"> Cancel </v-btn>
        <v-btn
          color="blue darken-1"
          text
          @click="add"
          :loading="saving"
          :disabled="
            saving ||
            (newProject.provider === 'aws' && !newProject.env.AWS_DEFAULT_REGION) ||
            (newProject.provider === 'openstack' && !newProject.env.OS_SUBNET_ID)
          "
        >
          Add
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
import ProjectRepository from "@/repositories/ProjectRepository";
import MessageDialog from "@/components/ui/MessageDialog";
import OpenStackSubnet from "@/components/ui/OpenStackSubnet";
import AwsCredentials from "@/components/ui/AWSCredentials";

export default {
  name: "CloudProviderInput",
  components: { MessageDialog, AwsCredentials, OpenStackSubnet },
  emits: ["newProject"],
  data() {
    return {
      dialog: false,
      saving: false,
      errorDialog: false,
      errorMessage: "",
      providers: ["openstack", "aws"],
      provider_var: {
        openstack: ["OS_AUTH_URL", "OS_APPLICATION_CREDENTIAL_ID", "OS_APPLICATION_CREDENTIAL_SECRET"],
        aws: [],
      },
      defaultProject: {
        name: "",
        provider: "openstack",
        agent_pool_name: "",
        max_instance_hourly_price: null,
        env: {
          OS_AUTH_URL: "",
          OS_APPLICATION_CREDENTIAL_ID: "",
          OS_APPLICATION_CREDENTIAL_SECRET: "",
        },
      },
      newProject: {
        name: "",
        provider: "openstack",
        agent_pool_name: "",
        max_instance_hourly_price: null,
        env: {
          OS_AUTH_URL: "",
          OS_APPLICATION_CREDENTIAL_ID: "",
          OS_APPLICATION_CREDENTIAL_SECRET: "",
        },
      },
    };
  },
  watch: {
    "newProject.provider"() {
      this.newProject.env = {};
      this.newProject.max_instance_hourly_price = null;
    },
    dialog(val) {
      val || this.close();
    },
  },
  methods: {
    async add() {
      this.saving = true;
      const payload = { ...this.newProject };
      if (!payload.agent_pool_name) {
        delete payload.agent_pool_name;
      }
      try {
        await ProjectRepository.post(payload);
      } catch (e) {
        this.errorMessage = e.response?.data?.message ?? "An error occurred while creating the project.";
        this.errorDialog = true;
        return;
      } finally {
        this.saving = false;
      }
      this.$emit("newProject");
      this.newProject = JSON.parse(JSON.stringify(this.defaultProject));
      this.close();
    },
    close() {
      this.dialog = false;
      this.$nextTick(() => {
        this.newProject = JSON.parse(JSON.stringify(this.defaultProject));
      });
    },
  },
};
</script>
