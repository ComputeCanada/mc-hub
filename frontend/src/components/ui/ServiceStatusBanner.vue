<template>
  <div v-if="visible" class="service-status mx-3 mt-3" role="status" aria-live="polite">
    <v-alert :type="disrupted.length ? 'warning' : 'info'" outlined class="mb-0">
      <strong>{{ heading }}</strong>
      <div v-if="disrupted.length">MC-Hub operations may be slower or fail.</div>
      <div v-if="unavailable">Status updates unavailable. Previously reported information may be out of date.</div>
      <v-btn
        text
        small
        :aria-expanded="String(expanded)"
        aria-controls="service-status-details"
        @click="expanded = !expanded"
      >
        {{ expanded ? "Hide details" : "Show details" }}
      </v-btn>
      <div v-if="expanded" id="service-status-details">
        <div v-for="provider in providers" :key="provider.provider" class="mt-3">
          <strong>{{ provider.name }}</strong> — {{ condition(provider) }}
          <div v-if="provider.affected_components.length">
            Affected components: {{ provider.affected_components.join(", ") }}
          </div>
          <div v-for="incident in provider.incidents" :key="incident.id" class="mt-1">
            <a :href="incident.url" target="_blank" rel="noopener noreferrer">{{ incident.title }}</a>
            — {{ incident.status }}{{ incident.confirmed ? "" : " (current status unconfirmed)" }}
            <div v-if="incident.updated_at" class="text-caption">
              Provider update: {{ formatDate(incident.updated_at) }}
            </div>
          </div>
          <div class="text-caption">Last successful check: {{ formatDate(provider.last_success_at) }}</div>
          <a :href="provider.status_url" target="_blank" rel="noopener noreferrer">View status page</a>
        </div>
      </div>
    </v-alert>
  </div>
</template>

<script>
// Advisory polling must not trigger the main repository's session-expiry reload
// when a temporary network failure prevents a status refresh.
import axios from "axios";

export default {
  data: () => ({
    providers: [],
    expanded: false,
    failed: false,
    clock: Date.now(),
    timer: null,
    pending: false,
    stopped: false,
  }),
  computed: {
    disrupted() {
      return this.providers.filter((p) => p.reported_status === "disruption");
    },
    unavailable() {
      return this.failed || this.providers.some((p) => this.stale(p));
    },
    visible() {
      return this.disrupted.length > 0 || this.unavailable;
    },
    heading() {
      if (!this.disrupted.length) return "Service status unavailable";
      const names = this.disrupted.map((p) => p.name);
      const subject = names.length <= 2 ? names.join(" and ") : `${names.length} service providers`;
      const uncertain =
        this.failed || this.disrupted.some((p) => this.stale(p) || p.incidents.some((i) => !i.confirmed));
      return `${subject} ${
        uncertain
          ? "last reported a service disruption"
          : names.length === 1
          ? "reports a service disruption"
          : "report service disruptions"
      }.`;
    },
  },
  mounted() {
    document.addEventListener("visibilitychange", this.refresh);
    this.refresh();
    this.timer = setInterval(this.refresh, 60000);
  },
  beforeDestroy() {
    this.stopped = true;
    clearInterval(this.timer);
    document.removeEventListener("visibilitychange", this.refresh);
  },
  methods: {
    stale(provider) {
      return (
        provider.freshness !== "fresh" ||
        !provider.last_success_at ||
        this.clock - Date.parse(provider.last_success_at) >= 180000
      );
    },
    condition(provider) {
      if (provider.reported_status === "disruption")
        return this.stale(provider) || this.failed
          ? "Disruption last reported; updates unavailable"
          : "Disruption reported";
      return this.stale(provider) || this.failed ? "Status unavailable" : "No active incidents reported";
    },
    formatDate(value) {
      return value ? new Date(value).toLocaleString() : "Not yet available";
    },
    async refresh() {
      if (document.hidden || this.pending || this.stopped) return;
      this.clock = Date.now();
      this.pending = true;
      try {
        const { data } = await axios.get(`${process.env.VUE_APP_API_URL || "/api"}/service-status`, { timeout: 10000 });
        if (!this.stopped) {
          this.providers = data.providers;
          this.failed = false;
        }
      } catch {
        if (!this.stopped) this.failed = true;
      } finally {
        this.pending = false;
      }
    },
  },
};
</script>
