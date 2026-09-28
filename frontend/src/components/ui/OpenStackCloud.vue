<template>
  <div>
    <v-select
      :model-value="selectedValue"
      :items="clouds"
      item-title="name"
      item-value="auth_url"
      label="OpenStack cloud"
      :loading="loading"
      :disabled="loading || clouds.length === 0"
      no-data-text="No approved OpenStack clouds configured"
      @update:model-value="$emit('update:modelValue', $event)"
    />
    <v-alert v-if="error" type="error" density="compact">{{ error }}</v-alert>
    <v-alert v-else-if="!loading && clouds.length === 0" type="info" density="compact">
      No OpenStack clouds are available. Ask the operator to configure an approved cloud.
    </v-alert>
    <v-btn v-if="error" variant="text" @click="loadClouds">Retry</v-btn>
  </div>
</template>

<script>
import ProjectRepository from "@/repositories/ProjectRepository";

export default {
  name: "OpenStackCloud",
  emits: ["update:modelValue"],
  props: { modelValue: { type: String, default: "" } },
  data() {
    return { clouds: [], loading: false, error: "", requestId: 0 };
  },
  computed: {
    selectedValue() {
      return this.clouds.some((cloud) => cloud.auth_url === this.modelValue) ? this.modelValue : null;
    },
  },
  created() {
    this.loadClouds();
  },
  beforeUnmount() {
    this.requestId++;
  },
  methods: {
    async loadClouds() {
      const id = ++this.requestId;
      this.loading = true;
      this.error = "";
      try {
        const { data } = await ProjectRepository.openstackClouds();
        if (id === this.requestId) this.clouds = data.clouds;
      } catch (error) {
        if (id !== this.requestId) return;
        this.clouds = [];
        this.error = "Unable to load approved OpenStack clouds.";
      } finally {
        if (id === this.requestId) this.loading = false;
      }
    },
  },
};
</script>
