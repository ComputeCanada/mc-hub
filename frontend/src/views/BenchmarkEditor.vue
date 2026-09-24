<template>
  <v-card max-width="900" class="mx-auto" :loading="loading">
    <v-card-title>{{ benchmarkId ? "Edit benchmark" : "New benchmark" }}</v-card-title>
    <v-card-text>
      <v-alert v-if="error" type="error">{{ error }}</v-alert>
      <v-alert v-if="saving" type="info"
        >Saving the benchmark and preparing its repository and Terraform workspace…</v-alert
      >
      <v-alert type="info" outlined>
        The first save creates the Git repository, Terraform files, and workspace. Each run creates fresh resources
        using the benchmark's cluster name, Git repository, and Terraform workspace. Resources are torn down after
        success, failure, or timeout. Cleanup retries block the next run. Times and schedules use UTC. Deployment
        changes create a new commit on the next run; results are grouped by commit and success criterion.
      </v-alert>
      <cluster-editor
        v-if="specs && projects.length"
        :specs="specs"
        :existing-cluster="false"
        benchmark-mode
        :identity-locked="identityLocked"
        :preserve-specs="!!benchmarkId"
        :project-ids="benchmarkId ? [projectId] : projects.map((p) => p.id)"
        :submit-disabled="saving"
        submit-label="Save benchmark"
        @apply="save"
      >
        <template #benchmark-fields>
          <v-text-field v-model="name" label="Benchmark name" :rules="[required, nameRule]" maxlength="120" />
          <v-select
            v-model="successCriterion"
            :items="successCriteria"
            label="Success criterion"
            hint="Time from Terraform Cloud apply start to this state. Cleanup starts as soon as the target is reached."
            persistent-hint
          />
          <v-row>
            <v-col cols="12" sm="4"><v-select v-model="frequency" :items="frequencies" label="Frequency" /></v-col>
            <v-col cols="12" sm="4"
              ><v-text-field
                v-model.number="timeout"
                type="number"
                label="Maximum run time (minutes)"
                min="10"
                max="1440"
                :rules="[timeoutRule]"
                hint="Includes cluster creation and planning."
                persistent-hint
            /></v-col>
            <v-col cols="12" sm="4"><v-switch v-model="enabled" label="Scheduled runs enabled" /></v-col>
          </v-row>
          <v-text-field
            v-model="nextRun"
            type="datetime-local"
            label="Next scheduled run (UTC)"
            hint="Leave empty to start one interval after saving. Missed schedules never create a backlog."
            persistent-hint
            clearable
          />
          <v-divider class="my-4" />
        </template>
      </cluster-editor>
      <v-alert v-else-if="!loading && !error" type="info"
        >A project administrator role is required to define benchmarks.</v-alert
      >
    </v-card-text>
  </v-card>
</template>
<script>
import ClusterEditor from "@/components/cluster/ClusterEditor";
import Repository from "@/repositories/Repository";
import TemplateRepository from "@/repositories/TemplateRepository";
export default {
  components: { ClusterEditor },
  props: { id: String },
  data: () => ({
    loading: true,
    saving: false,
    savedId: null,
    error: "",
    specs: null,
    projects: [],
    projectId: null,
    identityLocked: false,
    name: "",
    frequency: "daily",
    successCriterion: "healthy",
    successCriteria: [
      { text: "Build completed", value: "build_completed" },
      { text: "Provisioning completed (healthy)", value: "healthy" },
    ],
    timeout: 120,
    enabled: true,
    nextRun: "",
    frequencies: ["hourly", "daily", "weekly"],
    required: (value) => !!value?.trim() || "Required",
    nameRule: (value) => value.length <= 120 || "Use up to 120 characters",
    timeoutRule: (value) => (Number.isInteger(value) && value >= 10 && value <= 1440) || "Use 10–1440 minutes",
  }),
  computed: {
    benchmarkId() {
      return this.id || this.savedId;
    },
  },
  async created() {
    try {
      this.projects = (await Repository.get("/benchmarks")).data.projects;
      if (this.id) {
        const { benchmark } = (await Repository.get(`/benchmarks/${this.id}`)).data;
        if (benchmark.archived) throw new Error("Archived benchmarks cannot be edited.");
        this.specs = benchmark.configuration;
        this.projectId = benchmark.project_id;
        this.identityLocked = benchmark.identity_locked;
        this.error = benchmark.setup_error || "";
        this.name = benchmark.name;
        this.frequency = benchmark.frequency;
        this.successCriterion = benchmark.success_criterion;
        this.timeout = benchmark.timeout_minutes;
        this.enabled = benchmark.enabled;
        this.nextRun = benchmark.next_run_at.slice(0, 16);
      } else this.specs = (await TemplateRepository.get("default")).data;
    } catch (error) {
      this.error = error.response?.data?.message || error.message || "Unable to load the benchmark form.";
    } finally {
      this.loading = false;
    }
  },
  methods: {
    async save() {
      this.saving = true;
      this.error = "";
      try {
        const payload = {
          name: this.name,
          frequency: this.frequency,
          success_criterion: this.successCriterion,
          timeout_minutes: this.timeout,
          enabled: this.enabled,
          next_run_at: this.nextRun ? `${this.nextRun}:00Z` : null,
          project_id: this.specs.cloud.id,
          configuration: this.specs,
        };
        const response = this.benchmarkId
          ? await Repository.put(`/benchmarks/${this.benchmarkId}`, payload)
          : await Repository.post("/benchmarks", payload);
        this.$disableUnloadConfirmation();
        this.$router.push({ path: "/benchmarks", query: { benchmark: response.data.id } });
      } catch (error) {
        const saved = error.response?.data?.benchmark;
        if (saved) {
          this.savedId = saved.id;
          this.projectId = saved.project_id;
          this.identityLocked = saved.identity_locked;
        }
        this.error = error.response?.data?.message || "Unable to save benchmark.";
      } finally {
        this.saving = false;
      }
    },
  },
};
</script>
