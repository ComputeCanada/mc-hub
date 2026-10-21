<template>
  <v-alert v-if="message" :type="checking ? 'info' : 'warning'" class="my-3" role="status">
    {{ message }}
  </v-alert>
</template>

<script>
import ProjectRepository from "@/repositories/ProjectRepository";

const HEALTHY_CHECK_INTERVAL_MS = 5 * 60 * 1000;
const RECOVERY_CHECK_INTERVAL_MS = 30 * 1000;

export default {
  name: "AgentAvailability",
  props: { projectId: [Number, String] },
  emits: ["availability"],
  data: () => ({
    message: "",
    checking: true,
    timer: null,
    generation: 0,
  }),
  watch: {
    projectId: {
      immediate: true,
      handler() {
        clearTimeout(this.timer);
        const generation = ++this.generation;
        this.checking = true;
        this.message = this.projectId ? "Checking Terraform agent availability…" : "Select a project to check agent availability.";
        this.$emit("availability", false);
        if (this.projectId) this.check(generation);
      },
    },
  },
  beforeUnmount() {
    ++this.generation;
    clearTimeout(this.timer);
  },
  methods: {
    async check(generation) {
      let available = false;
      try {
        const { data } = await ProjectRepository.agentAvailability(this.projectId);
        if (generation !== this.generation) return;
        available = data.available === true;
        this.message = available ? "" : (data.message || "Terraform agent unavailable. Retrying automatically.");
        this.$emit("availability", available);
      } catch {
        if (generation !== this.generation) return;
        this.message = "Could not verify Terraform agent availability. Apply is disabled. Retrying automatically.";
        this.$emit("availability", false);
      } finally {
        if (generation === this.generation) {
          this.checking = false;
          this.timer = setTimeout(
            () => this.check(generation),
            available ? HEALTHY_CHECK_INTERVAL_MS : RECOVERY_CHECK_INTERVAL_MS
          );
        }
      }
    },
  },
};
</script>
