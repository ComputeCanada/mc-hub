<template>
  <v-container>
    <h1 class="text-h4 mb-4">Service adoption</h1>
    <v-alert v-if="error" type="error">{{ error }}</v-alert>
    <template v-if="authorized">
      <v-card class="pa-4 mb-4">
        <v-row align="center">
          <v-col cols="12" sm="3"><v-text-field v-model="start" label="From (UTC)" type="date" /></v-col>
          <v-col cols="12" sm="3"><v-text-field v-model="end" label="Through (UTC)" type="date" /></v-col>
          <v-col cols="12" sm="4"
            ><v-select
              v-model="project"
              :items="report ? report.projects : []"
              item-title="name"
              item-value="id"
              clearable
              label="All projects"
          /></v-col>
          <v-col cols="12" sm="2"><v-btn color="primary" :loading="loading" @click="load(1)">Update</v-btn></v-col>
        </v-row>
      </v-card>
      <v-progress-linear v-if="loading" indeterminate aria-label="Loading usage" />
      <template v-if="report">
        <v-alert type="info" variant="outlined">
          History begins {{ timestamp(report.tracking_started_at) }}. First-time creators means their first observed
          successful deployment since tracking began, across all projects. Existing deployments have unknown earlier
          history ({{ report.legacy_lifetimes }} retained lifetimes predate tracking). Creators are MC Hub users, not
          users of the resulting clusters.
        </v-alert>
        <v-alert v-if="stale" type="warning" variant="outlined"
          >Background observations are overdue. Deployment outcomes and timing may be incomplete.</v-alert
        >
        <p class="text-caption">
          Last background sweep: {{ timestamp(report.last_poll_at) }}. Sweeps run every
          {{ report.poll_interval_seconds }} seconds plus processing time. Healthy timestamps reflect first observation.
        </p>
        <v-row>
          <v-col v-for="metric in metrics" :key="metric.key" cols="6" md="4" lg="2">
            <v-card class="pa-4 fill-height"
              ><div class="text-h4">{{ report.summary[metric.key] }}</div>
              <div>{{ metric.title }}</div></v-card
            >
          </v-col>
        </v-row>
        <v-card class="my-4">
          <v-card-title>Monthly adoption</v-card-title>
          <v-card-subtitle
            >Deployments count when first healthy. Rebuilds count again; configuration updates do not.</v-card-subtitle
          >
          <v-data-table
            :headers="monthlyHeaders"
            :items="report.months"
            item-value="month"
            :items-per-page="12"
            :sort-by="[{ key: 'month', order: 'desc' }]"
          >
            <template v-slot:[`item.successful_deployments`]="{ item }">
              <div class="d-flex align-center">
                <span class="mr-3">{{ item.successful_deployments }}</span
                ><v-progress-linear
                  :model-value="(100 * item.successful_deployments) / maxDeployments"
                  height="8"
                  aria-hidden="true"
                />
              </div>
            </template>
          </v-data-table>
        </v-card>
        <v-row>
          <v-col cols="12" md="4"
            ><v-card class="pa-4 fill-height">
              <h2 class="text-h6">Apply to healthy</h2>
              <p>
                Average {{ duration(report.apply_to_healthy.average_seconds) }} · Median
                {{ duration(report.apply_to_healthy.median_seconds) }} · P95
                {{ duration(report.apply_to_healthy.p95_seconds) }}
              </p>
              <p class="text-caption">
                {{ report.apply_to_healthy.count }} successful timed applies requested in this period, including
                updates. {{ report.failed_attempts }} failed; {{ report.unfinished_attempts }} unfinished. Unknown
                acceptance times are excluded.
              </p>
            </v-card></v-col
          >
          <v-col cols="12" md="4"
            ><v-card class="pa-4 fill-height">
              <h2 class="text-h6">Completed lifetime</h2>
              <p>
                Average {{ duration(report.completed_lifetime.average_seconds) }} · Median
                {{ duration(report.completed_lifetime.median_seconds) }}
              </p>
              <p class="text-caption">
                {{ report.completed_lifetime.count }} lifetimes ending in this period, measured from accepted apply
                through completed teardown.
              </p>
            </v-card></v-col
          >
          <v-col cols="12" md="4"
            ><v-card class="pa-4 fill-height">
              <h2 class="text-h6">Ongoing deployment age</h2>
              <p>
                Average {{ duration(report.ongoing_age.average_seconds) }} · Median
                {{ duration(report.ongoing_age.median_seconds) }}
              </p>
              <p class="text-caption">
                {{ report.ongoing_age.count }} open lifetimes with known starts in the selected project, as of now,
                regardless of date range.
              </p>
            </v-card></v-col
          >
        </v-row>
        <v-card class="my-4">
          <v-card-title>Apply history</v-card-title>
          <v-card-subtitle>Attempts requested in the selected period. All timestamps are UTC.</v-card-subtitle>
          <v-data-table
            :headers="attemptHeaders"
            :items="report.attempts"
            item-value="id"
            hide-default-footer
            :items-per-page="25"
          >
            <template v-slot:[`item.duration_seconds`]="{ item }">{{ duration(item.duration_seconds) }}</template>
            <template v-slot:[`item.applied_at`]="{ item }">{{ timestamp(item.applied_at) }}</template>
            <template v-slot:[`item.healthy_at`]="{ item }">{{ timestamp(item.healthy_at) }}</template>
            <template v-slot:[`item.commit_sha`]="{ item }"
              ><code v-if="item.commit_sha">{{ item.commit_sha }}</code
              ><span v-else>Unknown</span></template
            >
          </v-data-table>
          <v-pagination
            v-if="report.attempt_count > 25"
            :model-value="report.page"
            :length="Math.ceil(report.attempt_count / 25)"
            :disabled="loading"
            @update:model-value="load"
          />
          <v-card-text>{{ report.attempt_count }} apply attempts</v-card-text>
        </v-card>
      </template>
    </template>
  </v-container>
</template>

<script>
import Repository from "@/repositories/Repository";
import UserRepository from "@/repositories/UserRepository";
const metrics = [
  { title: "Unique creators", key: "unique_creators" },
  { title: "First-time creators", key: "first_time_creators" },
  { title: "Returning creators", key: "returning_creators" },
  { title: "Successful deployments", key: "successful_deployments" },
  { title: "Distinct clusters", key: "distinct_clusters" },
  { title: "Active projects", key: "active_projects" },
];
export default {
  data() {
    const now = new Date();
    return {
      disposed: false,
      requestId: 0,
      authorized: false,
      loading: false,
      error: "",
      report: null,
      project: null,
      start: new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth() - 11, 1)).toISOString().slice(0, 10),
      end: now.toISOString().slice(0, 10),
      metrics,
      monthlyHeaders: [{ title: "Month", key: "month" }, ...metrics],
      attemptHeaders: [
        { title: "Cluster", key: "hostname" },
        { title: "Project", key: "project" },
        { title: "Creator", key: "creator" },
        { title: "Initiated by", key: "initiated_by" },
        { title: "Kind", key: "kind" },
        { title: "Outcome", key: "outcome" },
        { title: "Apply accepted", key: "applied_at" },
        { title: "First healthy", key: "healthy_at" },
        { title: "Duration", key: "duration_seconds" },
        { title: "Terraform run", key: "run_id" },
        { title: "Repository", key: "repository" },
        { title: "Applied commit", key: "commit_sha" },
      ],
    };
  },
  computed: {
    maxDeployments() {
      return Math.max(1, ...this.report.months.map((month) => month.successful_deployments));
    },
    stale() {
      return !this.report.last_poll_at || Date.now() - Date.parse(this.report.last_poll_at) > 180000;
    },
  },
  async created() {
    try {
      const { data } = await UserRepository.getCurrent();
      if (this.disposed) return;
      this.authorized = data.is_admin === true;
      if (this.authorized) await this.load(1);
      else this.error = "Only hub admins can view usage statistics.";
    } catch (error) {
      if (!this.disposed) this.error = "Unable to verify dashboard access.";
    }
  },
  beforeUnmount() {
    this.disposed = true;
    this.requestId++;
  },
  methods: {
    async load(page = 1) {
      if (!this.authorized || this.disposed) return;
      const requestId = ++this.requestId;
      this.loading = true;
      this.error = "";
      try {
        const report = (
          await Repository.get("/usage", {
            params: { start: this.start, end: this.end, project: this.project || undefined, page },
          })
        ).data;
        if (requestId === this.requestId) this.report = report;
      } catch (error) {
        if (requestId !== this.requestId) return;
        this.report = null;
        this.error = error.response?.data?.message || "Unable to load usage statistics.";
      } finally {
        if (requestId === this.requestId) this.loading = false;
      }
    },
    timestamp(value) {
      return value ? value.replace("T", " ").replace(/\.\d+Z$/, "Z") : "Unknown";
    },
    duration(seconds) {
      if (seconds === null || seconds === undefined) return "—";
      if (seconds < 60) return `${Math.round(seconds)} sec`;
      if (seconds < 3600) return `${(seconds / 60).toFixed(1)} min`;
      if (seconds < 86400) return `${(seconds / 3600).toFixed(1)} hr`;
      return `${(seconds / 86400).toFixed(1)} days`;
    },
  },
};
</script>
