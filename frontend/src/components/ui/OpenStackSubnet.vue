<template>
  <div>
    <div class="d-flex align-start">
      <v-select
        class="flex-grow-1"
        :model-value="modelValue.OS_SUBNET_ID"
        :items="subnetItems"
        item-title="name"
        item-value="id"
        label="OpenStack subnet"
        :disabled="loading"
        hint="All clusters in this project use this subnet"
        persistent-hint
        @update:model-value="setSubnet"
      />
      <v-btn class="ml-2 mt-4 flex-shrink-0" variant="text" :loading="loading" :disabled="loading" @click="loadSubnets"
        >refresh</v-btn
      >
    </div>
    <v-alert v-if="error" type="error" density="compact">{{ error }}</v-alert>
  </div>
</template>

<script>
import ProjectRepository from "@/repositories/ProjectRepository";

export default {
  name: "OpenStackSubnet",
  emits: ["update:modelValue"],
  props: { modelValue: { type: Object, required: true }, projectId: Number },
  data() {
    return { subnets: [], loading: false, error: "", requestId: 0 };
  },
  created() {
    if (this.projectId) this.loadSubnets();
  },
  computed: {
    subnetItems() {
      const selected = this.modelValue.OS_SUBNET_ID;
      if (this.projectId && selected && !this.subnets.some((subnet) => subnet.id === selected)) {
        return [{ id: selected, name: selected }, ...this.subnets];
      }
      return this.subnets;
    },
    credentials() {
      return JSON.stringify([
        this.modelValue.OS_AUTH_URL,
        this.modelValue.OS_APPLICATION_CREDENTIAL_ID,
        this.modelValue.OS_APPLICATION_CREDENTIAL_SECRET,
      ]);
    },
  },
  watch: {
    credentials() {
      this.requestId++;
      this.loading = false;
      this.subnets = [];
      this.error = "";
      if (this.projectId) return;
      const env = { ...this.modelValue };
      delete env.OS_SUBNET_ID;
      this.$emit("update:modelValue", env);
    },
  },
  beforeUnmount() {
    this.requestId++;
  },
  methods: {
    setSubnet(subnet) {
      this.$emit("update:modelValue", { ...this.modelValue, OS_SUBNET_ID: subnet });
    },
    async loadSubnets() {
      const id = ++this.requestId;
      this.loading = true;
      this.error = "";
      try {
        const payload = { env: this.modelValue };
        if (this.projectId) payload.project_id = this.projectId;
        const response = await ProjectRepository.openstackSubnets(payload);
        if (id === this.requestId) {
          this.subnets = response.data.subnets;
          if (!this.projectId && !this.subnets.some((subnet) => subnet.id === this.modelValue.OS_SUBNET_ID)) {
            this.setSubnet(undefined);
          }
        }
      } catch (error) {
        if (id === this.requestId)
          this.error = error.response?.data?.message || "Unable to load OpenStack subnets. Retry.";
      } finally {
        if (id === this.requestId) this.loading = false;
      }
    },
  },
};
</script>
