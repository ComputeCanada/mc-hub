<template>
  <div>
    <v-select
      :value="selectedValue"
      :items="clouds"
      item-text="name"
      item-value="auth_url"
      label="OpenStack cloud"
      :loading="loading"
      :disabled="loading || clouds.length === 0"
      no-data-text="No approved OpenStack clouds configured"
      @change="$emit('input', $event)"
    />
    <v-alert v-if="error" type="error" dense>{{ error }}</v-alert>
    <v-alert v-else-if="!loading && clouds.length === 0" type="info" dense>
      No OpenStack clouds are available. Ask the operator to configure an approved cloud.
    </v-alert>
    <v-btn v-if="error" text @click="loadClouds">Retry</v-btn>
  </div>
</template>

<script>
import ProjectRepository from "@/repositories/ProjectRepository";

export default {
  name: "OpenStackCloud",
  props: { value: { type: String, default: "" } },
  data() {
    return { clouds: [], loading: false, error: "" };
  },
  computed: {
    selectedValue() {
      return this.clouds.some((cloud) => cloud.auth_url === this.value) ? this.value : null;
    },
  },
  created() {
    this.loadClouds();
  },
  methods: {
    async loadClouds() {
      this.loading = true;
      this.error = "";
      try {
        this.clouds = (await ProjectRepository.openstackClouds()).data.clouds;
      } catch (error) {
        this.clouds = [];
        this.error = "Unable to load approved OpenStack clouds.";
      } finally {
        this.loading = false;
      }
    },
  },
};
</script>
