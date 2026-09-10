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
        :value="value.AWS_DEFAULT_REGION"
        :items="regions"
        label="AWS region"
        :disabled="locked || loading"
        :hint="locked ? 'Projects with clusters cannot change region' : 'All clusters in this project use this region'"
        persistent-hint
        @change="setRegion"
      />
      <v-btn class="ml-2 mt-4 flex-shrink-0" text :loading="loading" :disabled="loading || locked" @click="loadRegions"
        >refresh</v-btn
      >
    </div>
    <v-alert v-if="error" type="error" dense>{{ error }}</v-alert>
    <v-text-field
      v-model="max_instance_hourly_price"
      label="Maximum instance price (USD/hour)"
      type="number"
      min="0"
      step="any"
      clearable
      hint="Optional, per instance. Compute only; excludes storage and IP charges."
      persistent-hint
    />
  </div>
</template>

<script>
import ProjectRepository from "@/repositories/ProjectRepository";

export default {
  name: "AWSCredentials",
  props: { value: { type: Object, required: true }, projectId: Number, locked: Boolean },
  data() {
    return {
      accessKey: "",
      secretKey: "",
      sessionToken: "",
      regions: this.value.AWS_DEFAULT_REGION ? [this.value.AWS_DEFAULT_REGION] : [],
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
  methods: {
    credentialsChanged() {
      this.requestId++;
      this.loading = false;
      this.regions = this.locked ? [this.value.AWS_DEFAULT_REGION] : [];
      const env = {};
      if (this.accessKey || this.secretKey || this.sessionToken) {
        Object.assign(env, {
          AWS_ACCESS_KEY_ID: this.accessKey,
          AWS_SECRET_ACCESS_KEY: this.secretKey,
          AWS_SESSION_TOKEN: this.sessionToken,
        });
      }
      if (this.locked) env.AWS_DEFAULT_REGION = this.value.AWS_DEFAULT_REGION;
      this.$emit("input", env);
    },
    setRegion(region) {
      this.$emit("input", { ...this.value, AWS_DEFAULT_REGION: region });
    },
    async loadRegions() {
      const id = ++this.requestId;
      this.loading = true;
      this.error = "";
      try {
        const response = await ProjectRepository.awsRegions({ env: this.value, project_id: this.projectId });
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
