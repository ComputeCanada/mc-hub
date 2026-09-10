<template>
  <div>
    <div class="d-flex align-start">
      <v-select
        class="flex-grow-1"
        :value="value.OS_SUBNET_ID"
        :items="subnets"
        item-text="name"
        item-value="id"
        label="OpenStack subnet"
        :disabled="loading"
        hint="All clusters in this project use this subnet"
        persistent-hint
        @change="setSubnet"
      />
      <v-btn class="ml-2 mt-4 flex-shrink-0" text :loading="loading" :disabled="loading" @click="loadSubnets"
        >refresh</v-btn
      >
    </div>
    <v-alert v-if="error" type="error" dense>{{ error }}</v-alert>
  </div>
</template>

<script>
import ProjectRepository from "@/repositories/ProjectRepository";

export default {
  name: "OpenStackSubnet",
  props: { value: { type: Object, required: true } },
  data() {
    return { subnets: [], loading: false, error: "", requestId: 0 };
  },
  computed: {
    credentials() {
      return JSON.stringify([
        this.value.OS_AUTH_URL,
        this.value.OS_APPLICATION_CREDENTIAL_ID,
        this.value.OS_APPLICATION_CREDENTIAL_SECRET,
      ]);
    },
  },
  watch: {
    credentials() {
      this.requestId++;
      this.loading = false;
      this.subnets = [];
      this.error = "";
      const env = { ...this.value };
      delete env.OS_SUBNET_ID;
      this.$emit("input", env);
    },
  },
  methods: {
    setSubnet(subnet) {
      this.$emit("input", { ...this.value, OS_SUBNET_ID: subnet });
    },
    async loadSubnets() {
      const id = ++this.requestId;
      this.loading = true;
      this.error = "";
      try {
        const response = await ProjectRepository.openstackSubnets({ env: this.value });
        if (id === this.requestId) {
          this.subnets = response.data.subnets;
          if (!this.subnets.some((subnet) => subnet.id === this.value.OS_SUBNET_ID)) this.setSubnet(undefined);
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
