<template>
  <div>
    <v-text-field
      v-model="accessKey"
      label="AWS access key ID"
      :hint="projectId ? 'Leave credentials empty to keep existing' : ''"
      persistent-hint
    />
    <v-text-field v-model="secretKey" label="AWS secret access key" type="password" />
    <v-text-field v-model="sessionToken" label="AWS session token (optional)" type="password" />
    <div class="d-flex align-start">
      <v-select
        class="flex-grow-1"
        :model-value="modelValue.AWS_DEFAULT_REGION"
        :items="regions"
        label="AWS region"
        :disabled="locked || loading"
        :hint="locked ? 'Projects with clusters cannot change region' : 'All clusters in this project use this region'"
        persistent-hint
        @update:model-value="setRegion"
      />
      <v-btn
        class="ml-2 mt-4 flex-shrink-0"
        variant="text"
        :loading="loading"
        :disabled="loading || locked"
        @click="loadRegions"
        >refresh</v-btn
      >
    </div>
    <v-alert v-if="error" type="error" density="compact">{{ error }}</v-alert>
  </div>
</template>

<script>
import ProjectRepository from "@/repositories/ProjectRepository";

export default {
  name: "AWSCredentials",
  emits: ["update:modelValue"],
  props: { modelValue: { type: Object, required: true }, projectId: Number, locked: Boolean },
  data() {
    return {
      accessKey: "",
      secretKey: "",
      sessionToken: "",
      regions: this.modelValue.AWS_DEFAULT_REGION ? [this.modelValue.AWS_DEFAULT_REGION] : [],
      loading: false,
      error: "",
      requestId: 0,
    };
  },
  watch: {
    accessKey() {
      this.credentialsChanged();
    },
    secretKey() {
      this.credentialsChanged();
    },
    sessionToken() {
      this.credentialsChanged();
    },
  },
  beforeUnmount() {
    this.requestId++;
  },
  methods: {
    credentialsChanged() {
      this.requestId++;
      this.loading = false;
      this.regions = this.locked ? [this.modelValue.AWS_DEFAULT_REGION] : [];
      const env = {};
      if (this.accessKey || this.secretKey || this.sessionToken) {
        Object.assign(env, {
          AWS_ACCESS_KEY_ID: this.accessKey,
          AWS_SECRET_ACCESS_KEY: this.secretKey,
          AWS_SESSION_TOKEN: this.sessionToken,
        });
      }
      if (this.locked) env.AWS_DEFAULT_REGION = this.modelValue.AWS_DEFAULT_REGION;
      this.$emit("update:modelValue", env);
    },
    setRegion(region) {
      this.$emit("update:modelValue", { ...this.modelValue, AWS_DEFAULT_REGION: region });
    },
    async loadRegions() {
      const id = ++this.requestId;
      this.loading = true;
      this.error = "";
      try {
        const response = await ProjectRepository.awsRegions({ env: this.modelValue, project_id: this.projectId });
        if (id === this.requestId) this.regions = response.data.regions;
      } catch (error) {
        if (id === this.requestId) this.error = error.response?.data?.message || "Unable to load AWS regions. Retry.";
      } finally {
        if (id === this.requestId) this.loading = false;
      }
    },
  },
};
</script>
