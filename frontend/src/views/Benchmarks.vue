<template>
  <v-container>
    <div class="d-flex align-center mb-4">
      <h1 class="text-h4">Benchmarks</h1>
      <v-spacer /> <v-btn v-if="projects.length" color="primary" to="/benchmarks/new">New benchmark</v-btn>
    </div>
    <v-alert v-if="error" type="error">{{ error }}</v-alert>
    <v-progress-linear v-if="loading" indeterminate />
    <v-alert v-if="!loading && !projects.length" type="info"
      >Benchmarks are available for projects you administer.</v-alert
    >
    <v-card v-if="projects.length" class="pa-4 mb-4">
      <v-row
        ><v-col cols="12" sm="4"
          ><v-select v-model="project" :items="projects" item-text="name" item-value="id" label="Project" clearable
        /></v-col>
        <v-col cols="12" sm="6"
          ><v-select
            v-model="selected"
            :items="visibleBenchmarks"
            item-text="name"
            item-value="id"
            label="Benchmark"
            @change="loadReport"
        /></v-col>
        <v-col cols="12" sm="2"><v-switch v-model="archived" label="Show archived" /></v-col
      ></v-row>
      <p v-if="!visibleBenchmarks.length">No benchmarks yet. Create one using your cluster specifications.</p>
    </v-card>
    <template v-if="report">
      <v-card class="pa-4 mb-4">
        <h2 class="text-h5">{{ report.benchmark.name }}</h2>
        <p>
          {{ report.benchmark.frequency }} · {{ report.benchmark.enabled ? "Scheduled" : "Paused" }} · Next scheduled
          run: {{ timestamp(report.benchmark.next_run_at) }} · Maximum run time:
          {{ report.benchmark.timeout_minutes }} minutes
        </p>
        <p>Success criterion: {{ criterionLabel(report.benchmark.success_criterion) }}</p>
        <v-alert v-if="report.benchmark.active_run" type="info" outlined
          >Current run: {{ report.benchmark.active_run }}. The next run is blocked until cleanup finishes.</v-alert
        >
        <template v-if="!report.benchmark.archived">
          <v-alert v-if="report.benchmark.setup_status !== 'ready'" type="warning" outlined>
            {{ report.benchmark.setup_error || "Repository and workspace setup is incomplete." }}
            Edit and save this benchmark to finish setup before running it.
          </v-alert>
          <v-btn
            class="mr-2"
            color="primary"
            :disabled="report.benchmark.setup_status !== 'ready' || !!report.benchmark.active_run || busy"
            @click="runNow"
            >Run now</v-btn
          >
          <v-btn class="mr-2" outlined :to="`/benchmarks/${selected}/edit`">Edit</v-btn>
          <v-btn class="mr-2" outlined :disabled="busy" @click="toggleEnabled">{{
            report.benchmark.enabled ? "Pause schedule" : "Enable schedule"
          }}</v-btn>
          <v-btn text color="error" :disabled="busy" @click="archive">Archive</v-btn>
        </template>
      </v-card>
      <v-select
        v-model="comparisonGroup"
        :items="comparisonOptions"
        label="Commit and success criterion"
        hint="Each group contains runs of one Git commit with the same success criterion. Name and schedule edits keep the same commit."
        persistent-hint
        class="mb-4"
      />
      <p v-if="selectedGroup" class="text-caption">
        {{ selectedGroup.total_runs }} runs in this group · Commit {{ selectedGroup.commit_sha }} ·
        {{ criterionLabel(selectedGroup.success_criterion) }} · Repository {{ selectedGroup.repository || "Unknown" }}.
        Run history retains all groups.
      </p>
      <p v-if="report.unassigned_runs" class="text-caption">
        {{ report.unassigned_runs }} runs have no recorded commit and appear only in the history.
      </p>
      <v-row
        ><v-col v-for="card in cards" :key="card.label" cols="6" md="3"
          ><v-card class="pa-4"
            ><div class="text-h5">{{ card.value }}</div>
            {{ card.label }}</v-card
          ></v-col
        ></v-row
      >
      <v-card class="my-4 pa-4">
        <h2 class="text-h6">{{ timingLabel }} over time</h2>
        <p v-if="isBuildComparison" class="text-caption">
          Terraform Cloud apply start to apply finish. Queue time and worker polling delays are excluded. Older build
          results without Terraform timestamps remain in history but are excluded from timing comparisons.
        </p>
        <p v-else class="text-caption">
          Terraform Cloud apply start to first observation of healthy services. Successful runs with known Terraform
          apply start times only. Older results without these timestamps are excluded from timing comparisons. Later health changes do not change a result.
        </p>
        <svg
          v-if="points.length"
          viewBox="0 0 800 200"
          role="img"
          aria-label="Benchmark deployment duration trend"
          style="width: 100%; max-height: 260px"
        >
          <line x1="45" y1="170" x2="780" y2="170" stroke="#999" />
          <text x="0" y="20" font-size="12">{{ duration(maxDuration) }}</text>
          <polyline
            :points="points.map((p) => `${p.x},${p.y}`).join(' ')"
            fill="none"
            stroke="#1976d2"
            stroke-width="2"
          />
          <circle v-for="point in points" :key="point.id" :cx="point.x" :cy="point.y" r="4" fill="#1976d2">
            <title>
              {{ timestamp(point.measurement_started_at) }}: {{ duration(point.duration_seconds) }} (revision
              {{ point.revision }})
            </title>
          </circle>
          <text x="45" y="193" font-size="12">{{ points[0].measurement_started_at.slice(0, 10) }}</text>
          <text x="780" y="193" text-anchor="end" font-size="12">
            {{ points[points.length - 1].measurement_started_at.slice(0, 10) }}
          </text>
        </svg>
        <p v-else>No successful timed runs for this group in the latest 500 runs.</p>
      </v-card>
      <v-card>
        <v-card-title>Run history</v-card-title>
        <v-card-subtitle
          >{{ report.total_runs }} runs · Showing the latest {{ report.runs.length }} · All times UTC. Expand a run for
          specifications and diagnostics.</v-card-subtitle
        >
        <v-data-table
          :headers="headers"
          :items="report.runs"
          item-key="id"
          show-expand
          :sort-by="['requested_at']"
          :sort-desc="[true]"
        >
          <template v-slot:[`item.requested_at`]="{ item }">{{ timestamp(item.requested_at) }}</template>
          <template v-slot:[`item.duration_seconds`]="{ item }">{{ duration(item.duration_seconds) }}</template>
          <template v-slot:[`item.success_criterion`]="{ item }">{{ criterionLabel(item.success_criterion) }}</template>
          <template v-slot:[`item.commit_sha`]="{ item }">
            <span :title="item.commit_sha">{{ item.commit_sha ? item.commit_sha.slice(0, 12) : "Unknown" }}</span>
          </template>
          <template v-slot:[`item.outcome`]="{ item }"
            ><v-chip small :color="item.outcome === 'successful' ? 'success' : item.outcome ? 'error' : undefined">{{
              item.outcome || (item.phase === "queued" ? (item.error ? "Postponed" : "Queued") : "In progress")
            }}</v-chip></template
          >
          <template v-slot:[`item.cleanup_at`]="{ item }">{{
            item.cleanup_at
              ? "Complete"
              : item.cleanup_error
              ? "Retrying — expand for details"
              : item.phase === "cleanup"
              ? "Pending"
              : "Not started"
          }}</template>
          <template #expanded-item="{ headers, item }"
            ><td :colspan="headers.length" class="pa-4">
              <v-alert v-if="item.error" :type="item.phase === 'queued' ? 'warning' : 'error'" outlined>{{
                item.error
              }}</v-alert>
              <p v-if="item.phase === 'queued' && item.error">
                Next status check: {{ timestamp(item.next_attempt_at) }}
              </p>
              <v-alert v-if="item.cleanup_error" type="warning" outlined>{{ item.cleanup_error }}</v-alert>
              <p>Cluster: {{ item.hostname }} · Apply accepted: {{ timestamp(item.applied_at) }}</p>
              <p v-if="item.success_criterion === 'build_completed' && item.apply_started_at">
                Terraform apply started: {{ timestamp(item.apply_started_at) }} · Terraform apply finished:
                {{ timestamp(item.target_reached_at) }} (Build completed)
              </p>
              <p v-else-if="item.success_criterion === 'build_completed'">
                Terraform apply timestamps unavailable; excluded from timing comparisons.
                <span v-if="item.target_reached_at"
                  >Previously observed target: {{ timestamp(item.target_reached_at) }}.</span
                >
              </p>
              <p v-else>
                Terraform apply started: {{ timestamp(item.apply_started_at) }} · Target reached: {{ timestamp(item.target_reached_at) }} ({{ criterionLabel(item.success_criterion) }})
              </p>
              <p>
                Terraform run: {{ item.terraform_run_id || "Unknown" }} · Repository:
                {{ item.repository || "Unknown" }} · Commit: {{ item.commit_sha || "Unknown" }}
              </p>
              <pre class="benchmark-specs">{{ JSON.stringify(item.configuration, null, 2) }}</pre>
            </td></template
          >
        </v-data-table>
      </v-card>
    </template>
  </v-container>
</template>
<script>
import Repository from "@/repositories/Repository";
export default {
  data: () => ({
    projects: [],
    benchmarks: [],
    project: null,
    selected: null,
    archived: false,
    report: null,
    comparisonGroup: null,
    loading: true,
    busy: false,
    error: "",
    timer: null,
    disposed: false,
    headers: [
      { text: "Requested", value: "requested_at" },
      { text: "Revision", value: "revision" },
      { text: "Commit", value: "commit_sha" },
      { text: "Outcome", value: "outcome" },
      { text: "Success criterion", value: "success_criterion" },
      { text: "Duration", value: "duration_seconds" },
      { text: "Phase", value: "phase" },
      { text: "Cleanup", value: "cleanup_at" },
    ],
  }),
  computed: {
    comparisonOptions() {
      return this.report.comparison_groups.map((group) => ({
        value: group.id,
        text: `${group.commit_sha.slice(0, 12)} · ${this.criterionLabel(group.success_criterion)} · ${
          group.total_runs
        } runs`,
      }));
    },
    selectedGroup() {
      return this.report.comparison_groups.find((group) => group.id === this.comparisonGroup);
    },
    isBuildComparison() {
      return (this.selectedGroup?.success_criterion || this.report.benchmark.success_criterion) === "build_completed";
    },
    timingLabel() {
      return this.isBuildComparison ? "Terraform apply duration" : "Apply to healthy";
    },
    visibleBenchmarks() {
      return this.benchmarks.filter(
        (b) => (!this.project || b.project_id === this.project) && (this.archived || !b.archived)
      );
    },
    cards() {
      return [
        { label: "Average", value: this.duration(this.selectedGroup?.timing.average_seconds) },
        { label: "Median", value: this.duration(this.selectedGroup?.timing.median_seconds) },
        { label: "P95", value: this.duration(this.selectedGroup?.timing.p95_seconds) },
        {
          label: "Success rate",
          value:
            this.selectedGroup?.success_rate == null ? "—" : `${Math.round(this.selectedGroup.success_rate * 100)}%`,
        },
      ];
    },
    timedRuns() {
      if (!this.selectedGroup) return [];
      return this.report.runs
        .filter(
          (r) =>
            r.outcome === "successful" &&
            r.duration_seconds != null &&
            r.measurement_started_at &&
            r.success_criterion === this.selectedGroup.success_criterion &&
            r.commit_sha === this.selectedGroup.commit_sha &&
            r.repository === this.selectedGroup.repository
        )
        .slice()
        .reverse();
    },
    maxDuration() {
      return Math.max(1, ...this.timedRuns.map((r) => r.duration_seconds));
    },
    points() {
      const runs = this.timedRuns;
      if (!runs.length) return [];
      const start = Date.parse(runs[0].measurement_started_at);
      const span = Date.parse(runs[runs.length - 1].measurement_started_at) - start || 1;
      return runs.map((r) => ({
        ...r,
        x: 45 + (735 * (Date.parse(r.measurement_started_at) - start)) / span,
        y: 170 - (145 * r.duration_seconds) / this.maxDuration,
      }));
    },
  },
  watch: {
    visibleBenchmarks(values) {
      if (!values.some((b) => b.id === this.selected)) {
        this.selected = values[0]?.id || null;
        this.loadReport();
      }
    },
  },
  async created() {
    this.selected = this.$route.query.benchmark || null;
    await this.refresh();
    this.timer = setInterval(() => {
      if (!this.busy) this.refresh();
    }, 15000);
  },
  beforeDestroy() {
    this.disposed = true;
    clearInterval(this.timer);
  },
  methods: {
    criterionLabel(value) {
      return value === "build_completed" ? "Build completed" : "Provisioning completed (healthy)";
    },
    async refresh() {
      try {
        this.error = "";
        const { data } = await Repository.get("/benchmarks");
        if (this.disposed) return;
        this.projects = data.projects;
        this.benchmarks = data.benchmarks;
        await this.loadReport();
      } catch (error) {
        this.report = null;
        this.error = error.response?.data?.message || "Unable to load benchmarks.";
      } finally {
        this.loading = false;
      }
    },
    async loadReport() {
      const selected = this.selected;
      if (!selected) {
        this.report = null;
        return;
      }
      try {
        const { data } = await Repository.get(`/benchmarks/${selected}`);
        if (!this.disposed && selected === this.selected) {
          const sameBenchmark = this.report?.benchmark.id === data.benchmark.id;
          if (!sameBenchmark || !data.comparison_groups.some((group) => group.id === this.comparisonGroup)) {
            this.comparisonGroup = data.default_comparison_group;
          }
          this.report = data;
        }
      } catch (error) {
        this.report = null;
        this.error = error.response?.data?.message || "Unable to load results.";
      }
    },
    async action(callback) {
      this.busy = true;
      try {
        await callback();
        await this.refresh();
      } catch (error) {
        this.error = error.response?.data?.message || "Unable to update benchmark.";
      } finally {
        this.busy = false;
      }
    },
    runNow() {
      return this.action(() => Repository.post(`/benchmarks/${this.selected}/run`));
    },
    toggleEnabled() {
      return this.action(() =>
        Repository.patch(`/benchmarks/${this.selected}`, {
          enabled: !this.report.benchmark.enabled,
        })
      );
    },
    archive() {
      if (
        window.confirm(
          "Archive this benchmark? Future runs stop. Active runs will finish cleanup and history is retained."
        )
      )
        return this.action(() => Repository.delete(`/benchmarks/${this.selected}`));
    },
    timestamp(value) {
      return value ? value.replace("T", " ").replace(/\.\d+Z$/, "Z") : "Unknown";
    },
    duration(value) {
      return value === null || value === undefined
        ? "—"
        : value < 60
        ? `${Math.round(value)} sec`
        : `${(value / 60).toFixed(1)} min`;
    },
  },
};
</script>
<style scoped>
.benchmark-specs {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
</style>
