<template>
  <v-alert :type="previous ? 'info' : 'error'" outlined class="mb-5" role="status" aria-live="polite">
    <h3>{{ previous ? "Previous attempt failed" : title }}</h3>
    <p v-if="!previous && (!failure || failure.phase !== 'plan')">Some changes may already have completed.</p>
    <p v-if="failure && (failure.failed_at || failure.observed_at)" class="text-caption">
      {{ failure.failed_at ? "Failed" : "Failure detected" }}: {{ failure.failed_at || failure.observed_at }}
    </p>
    <p v-if="diagnostic" class="diagnostic-summary">{{ diagnostic.split("\n")[0] }}</p>
    <p v-else>{{ fallback }}</p>
    <details v-if="diagnostic">
      <summary>Terraform diagnostic</summary>
      <pre class="diagnostic">{{ diagnostic }}</pre>
    </details>
    <p v-if="!previous && failure && failure.timeout" class="mt-3">
      This operation timed out. Retrying may resolve the issue. Review a new plan before applying again.
    </p>
    <p v-if="!previous" class="mt-3">If you need help, share these details with your administrator.</p>
    <p v-if="failure && failure.run_id" class="text-caption">Terraform run: {{ failure.run_id }}</p>
    <v-btn v-if="!previous && failure && failure.timeout" :disabled="busy" color="primary" @click="$emit('retry')">
      Review a new plan
    </v-btn>
    <v-btn text @click="copy">Copy error details</v-btn>
    <span aria-live="polite">{{ copyMessage }}</span>
  </v-alert>
</template>

<script>
export default {
  name: "ClusterFailure",
  props: {
    failure: { type: Object, default: null },
    hostname: String,
    status: String,
    previous: Boolean,
    busy: Boolean,
  },
  data: () => ({ copyMessage: "" }),
  computed: {
    title() {
      if (this.status === "destroy_error") return "Teardown failed";
      if (this.failure?.phase === "plan") return "Plan generation failed";
      if (this.status === "build_error") return "Your plan could not be fully applied";
      return "Terraform run failed";
    },
    diagnostic() {
      return this.failure?.diagnostic || "";
    },
    fallback() {
      return this.failure?.diagnostic_available === false
        ? "Terraform diagnostic details could not be retrieved."
        : "Terraform did not provide additional error details.";
    },
  },
  methods: {
    async copy() {
      const text = [
        this.hostname,
        this.title,
        this.failure?.run_id,
        this.failure?.failed_at || this.failure?.observed_at,
        this.diagnostic || this.fallback,
      ]
        .filter(Boolean)
        .join("\n\n");
      try {
        await navigator.clipboard.writeText(text);
        this.copyMessage = "Details copied.";
      } catch {
        this.copyMessage = "Could not copy. Select and copy the diagnostic text manually.";
      }
    },
  },
};
</script>

<style scoped>
.diagnostic,
.diagnostic-summary {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.diagnostic {
  max-height: 20rem;
  overflow-y: auto;
  margin-top: 0.75rem;
}
summary {
  cursor: pointer;
}
</style>
