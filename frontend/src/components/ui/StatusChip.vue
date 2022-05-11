<template>
  <div>
    <v-chip label :color="formattedStatus.color" dark v-if="status !== null">{{ formattedStatus.text }}</v-chip>
  </div>
</template>

<script>
const ClusterFormattedStatus = Object.freeze({
  created: { text: "Plan created", color: "darkgrey" },
  plan_running: { text: "Creating plan", color: "orange" },
  build_running: { text: "Build running", color: "orange" },
  provisioning_running: { text: "Provisioning running", color: "orange" },
  provisioning_success: { text: "Healthy", color: "green" },
  provisioning_error: { text: "Provisioning error", color: "red" },
  build_error: { text: "Build error", color: "red" },
  destroy_running: { text: "Destroy running", color: "orange" },
  destroy_error: { text: "Destroy error", color: "red" },
  not_found: { text: "Not found", color: "purple" },
});

export default {
  name: "StatusChip",
  props: {
    status: {
      required: true,
      validator: (value) => value === null || typeof value === "string",
    },
  },
  computed: {
    formattedStatus() {
      if (this.status === null) {
        return "";
      } else {
        return ClusterFormattedStatus[this.status];
      }
    },
  },
};
</script>

<style scoped></style>
