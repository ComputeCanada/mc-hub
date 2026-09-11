<template>
  <v-dialog v-model="dialog" max-width="500px">
    <template v-slot:activator="{ on, attrs }">
      <v-btn color="secondary" text v-bind="attrs" v-on="on" :disabled="!admin">
        <v-icon>mdi-pencil</v-icon> edit
      </v-btn>
    </template>
    <message-dialog v-model="errorDialog" type="error">{{ errorMessage }}</message-dialog>
    <v-card>
      <v-card-title>
        <span class="text-h5">Edit project</span>
      </v-card-title>
      <v-card-text>
        <v-container>
          <v-list>
            <template v-if="admin && project.provider === 'openstack'">
              <v-subheader>Cloud Credentials</v-subheader>
              <v-list-item>
                <open-stack-credentials v-model="env" :project-id="id" :cloud-name="project.cloud_name" />
              </v-list-item>
            </template>
            <aws-credentials
              v-if="admin && project.provider === 'aws'"
              v-model="awsEnv"
              :project-id="id"
              :locked="project.nb_clusters > 0"
            />
            <v-text-field
              v-if="admin && project.provider === 'aws'"
              v-model="maxInstanceHourlyPrice"
              label="Maximum instance price (USD/hour)"
              type="number"
              min="0"
              step="any"
              clearable
              hint="Optional, per instance. Compute only; excludes storage and IP charges."
              persistent-hint
            />
          </v-list>
        </v-container>
      </v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn color="blue darken-1" text @click="close"> Cancel </v-btn>
        <v-btn color="blue darken-1" text @click="save"> Save </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
import ProjectRepository from "@/repositories/ProjectRepository";
import MessageDialog from "@/components/ui/MessageDialog";
import AwsCredentials from "@/components/ui/AWSCredentials";
import OpenStackCredentials from "@/components/ui/OpenStackCredentials";

export default {
  name: "ProjectEditor",
  components: { MessageDialog, AwsCredentials, OpenStackCredentials },
  props: {
    id: { type: Number, required: true },
    admin: { type: Boolean, default: false },
  },
  data() {
    return {
      dialog: false,
      errorDialog: false,
      errorMessage: "",
      project: {},
      awsEnv: {},
      maxInstanceHourlyPrice: null,
      env: { OS_APPLICATION_CREDENTIAL_ID: "", OS_APPLICATION_CREDENTIAL_SECRET: "" },
    };
  },
  watch: {
    async dialog(val) {
      if (val) {
        this.project = (await ProjectRepository.get(this.id)).data;
        if (this.project.provider === "openstack") {
          this.env = {
            OS_APPLICATION_CREDENTIAL_ID: "",
            OS_APPLICATION_CREDENTIAL_SECRET: "",
            OS_SUBNET_ID: this.project.subnet_id,
          };
        }
        this.awsEnv = { AWS_DEFAULT_REGION: this.project.region };
        this.maxInstanceHourlyPrice = this.project.max_instance_hourly_price ?? null;
      } else {
        this.close();
      }
    },
  },
  methods: {
    async save() {
      const payload = {};
      if (this.admin && this.project.provider === "aws") {
        payload.max_instance_hourly_price = this.maxInstanceHourlyPrice === "" ? null : this.maxInstanceHourlyPrice;
      }
      if (
        this.project.provider === "aws" &&
        (this.awsEnv.AWS_ACCESS_KEY_ID !== undefined ||
          (this.awsEnv.AWS_DEFAULT_REGION && this.awsEnv.AWS_DEFAULT_REGION !== this.project.region))
      ) {
        payload.env = this.awsEnv;
      }
      if (this.project.provider === "openstack") {
        const { OS_APPLICATION_CREDENTIAL_ID: credentialId, OS_APPLICATION_CREDENTIAL_SECRET: secret } = this.env;
        if (Boolean(credentialId) !== Boolean(secret)) {
          this.errorMessage = "All credential fields must be filled to update credentials.";
          this.errorDialog = true;
          return;
        }
        const env = {};
        if (credentialId && secret) {
          env.OS_APPLICATION_CREDENTIAL_ID = credentialId;
          env.OS_APPLICATION_CREDENTIAL_SECRET = secret;
        }
        if (this.env.OS_SUBNET_ID && this.env.OS_SUBNET_ID !== this.project.subnet_id) {
          env.OS_SUBNET_ID = this.env.OS_SUBNET_ID;
        }
        if (Object.keys(env).length) payload.env = env;
      }
      if (!Object.keys(payload).length) {
        this.close();
        return;
      }
      try {
        await ProjectRepository.patch(this.id, payload);
      } catch (e) {
        this.errorMessage = e.response?.data?.message ?? "An error occurred while saving the project.";
        this.errorDialog = true;
        return;
      }
      this.close();
    },
    close() {
      this.project = {};
      this.env = { OS_APPLICATION_CREDENTIAL_ID: "", OS_APPLICATION_CREDENTIAL_SECRET: "" };
      this.dialog = false;
    },
  },
};
</script>
