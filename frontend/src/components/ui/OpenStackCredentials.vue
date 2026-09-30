<template>
  <div>
    <v-text-field v-if="projectId" :model-value="cloudName || 'Unknown cloud'" label="OpenStack cloud" readonly />
    <open-stack-cloud v-else v-model="authUrl" />
    <v-text-field
      v-model="credentialId"
      label="OpenStack application credential ID"
      :hint="projectId ? 'Leave credentials empty to keep existing' : ''"
      persistent-hint
    />
    <v-text-field v-model="credentialSecret" label="OpenStack application credential secret" type="password" />
    <open-stack-subnet
      :model-value="modelValue"
      :project-id="projectId"
      @update:model-value="$emit('update:modelValue', $event)"
    />
  </div>
</template>

<script>
import OpenStackCloud from "@/components/ui/OpenStackCloud";
import OpenStackSubnet from "@/components/ui/OpenStackSubnet";

export default {
  name: "OpenStackCredentials",
  emits: ["update:modelValue"],
  components: { OpenStackCloud, OpenStackSubnet },
  props: { modelValue: { type: Object, required: true }, projectId: Number, cloudName: String },
  computed: {
    authUrl: {
      get() {
        return this.modelValue.OS_AUTH_URL || "";
      },
      set(value) {
        this.$emit("update:modelValue", { ...this.modelValue, OS_AUTH_URL: value });
      },
    },
    credentialId: {
      get() {
        return this.modelValue.OS_APPLICATION_CREDENTIAL_ID || "";
      },
      set(value) {
        this.$emit("update:modelValue", { ...this.modelValue, OS_APPLICATION_CREDENTIAL_ID: value });
      },
    },
    credentialSecret: {
      get() {
        return this.modelValue.OS_APPLICATION_CREDENTIAL_SECRET || "";
      },
      set(value) {
        this.$emit("update:modelValue", { ...this.modelValue, OS_APPLICATION_CREDENTIAL_SECRET: value });
      },
    },
  },
};
</script>
