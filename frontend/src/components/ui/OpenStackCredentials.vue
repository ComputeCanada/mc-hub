<template>
  <div>
    <v-text-field v-if="projectId" :value="cloudName || 'Unknown cloud'" label="OpenStack cloud" readonly />
    <open-stack-cloud v-else v-model="authUrl" />
    <v-text-field
      v-model="credentialId"
      label="OpenStack application credential ID"
      :hint="projectId ? 'Leave credentials empty to keep existing' : ''"
      persistent-hint
    />
    <v-text-field v-model="credentialSecret" label="OpenStack application credential secret" type="password" />
    <open-stack-subnet :value="value" :project-id="projectId" @input="$emit('input', $event)" />
  </div>
</template>

<script>
import OpenStackCloud from "@/components/ui/OpenStackCloud";
import OpenStackSubnet from "@/components/ui/OpenStackSubnet";

export default {
  name: "OpenStackCredentials",
  components: { OpenStackCloud, OpenStackSubnet },
  props: { value: { type: Object, required: true }, projectId: Number, cloudName: String },
  computed: {
    authUrl: {
      get() {
        return this.value.OS_AUTH_URL || "";
      },
      set(value) {
        this.$emit("input", { ...this.value, OS_AUTH_URL: value });
      },
    },
    credentialId: {
      get() {
        return this.value.OS_APPLICATION_CREDENTIAL_ID || "";
      },
      set(value) {
        this.$emit("input", { ...this.value, OS_APPLICATION_CREDENTIAL_ID: value });
      },
    },
    credentialSecret: {
      get() {
        return this.value.OS_APPLICATION_CREDENTIAL_SECRET || "";
      },
      set(value) {
        this.$emit("input", { ...this.value, OS_APPLICATION_CREDENTIAL_SECRET: value });
      },
    },
  },
};
</script>
