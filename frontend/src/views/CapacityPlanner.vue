<template>
  <v-container>
    <h1 class="text-h4 mb-4">Project capacity planner</h1>
    <v-select v-model="projectId" :items="projects" item-text="name" item-value="id" label="Project" @change="load" />
    <v-alert v-if="error" type="error">{{ error }}</v-alert>
    <v-alert v-if="notice" type="success">{{ notice }}</v-alert>
    <v-alert type="info">
      Plans help your project coordinate resource usage. They do not reserve cloud capacity.
    </v-alert>
    <v-btn color="primary" class="mr-2 mb-4" :disabled="!projectId || loading" @click="newPlan"
      >Plan resource usage</v-btn
    >
    <v-btn class="mb-4" :loading="loading" @click="load">Refresh</v-btn>
    <v-alert v-if="report.warning" type="warning">{{ report.warning }}</v-alert>
    <v-alert
      v-if="report.preflight && report.preflight.status !== 'no_upcoming_plans'"
      :type="report.preflight.status === 'sufficient' ? 'success' : 'warning'"
    >
      <strong>24-hour quota check</strong> — {{ formatDate(report.preflight.checked_at) }}
      <div v-if="report.preflight.status === 'insufficient'">
        Current available quota is insufficient for the upcoming plans.
      </div>
      <div v-else-if="report.preflight.status === 'sufficient'">
        Current available quota covers the plans starting within 24 hours, assuming current usage continues.
      </div>
      <div v-else>Could not verify current quota. The worker will retry.</div>
      <div
        v-for="check in report.preflight.checks.filter((check) => Object.keys(check.shortages).length)"
        :key="check.starts_at"
      >
        {{ formatDateOnly(check.starts_at) }}: short by {{ resources(check.shortages) }}.
      </div>
      <div v-if="report.preflight.status === 'insufficient' && !report.preflight.notifications_enabled">
        External notifications are not configured. This warning is available in the planner.
      </div>
    </v-alert>
    <v-card v-if="specs" max-width="900" class="mx-auto mb-6">
      <v-card-title>{{ editingId === null ? "New capacity plan" : "Edit capacity plan" }}</v-card-title>
      <v-card-text>
        <cluster-editor
          :key="editingId === null ? 'new' : editingId"
          :preserve-specs="editingId !== null"
          :specs="specs"
          :existing-cluster="false"
          planner-mode
          :auto-create="autoCreate"
          :project-ids="[projectId]"
          :submit-label="checkedPayload ? 'Save plan' : 'Check planned capacity'"
          :submit-disabled="saving"
          @apply="checkedPayload ? save() : preview()"
          @cancel="closeForm"
        >
          <template #benchmark-fields>
            <v-row>
              <v-col cols="6">
                <v-text-field v-model="startsAt" type="date" label="Start date" :rules="[periodRule]" />
              </v-col>
              <v-col cols="6">
                <v-text-field v-model="endsAt" type="date" label="End date" :rules="[periodRule]" />
              </v-col>
            </v-row>
            <p>
              Dates use your local timezone. The period starts at midnight on the start date and ends at midnight at the
              beginning of the end date, when MC-Hub will tear down the cluster and delete its data.
            </p>
            <v-checkbox v-model="autoCreate" label="Automatically create the cluster at the start time" />
            <p v-if="autoCreate">
              Creation begins at the start time; provisioning takes additional time. If creation fails, review the
              cluster before trying manually.
            </p>
          </template>
        </cluster-editor>
        <v-alert v-if="previewReport" :type="hasShortages(previewReport) ? 'warning' : 'success'">
          {{
            hasShortages(previewReport)
              ? "Insufficient quota during this period. You can still save this plan."
              : "This plan fits the estimated quota for the period."
          }}
          <div v-for="(segment, index) in conflicts" :key="index">
            {{ formatDate(segment.starts_at) }} – {{ formatDate(segment.ends_at) }}: short by
            {{ resources(segment.shortages) }}
          </div>
        </v-alert>
      </v-card-text>
    </v-card>
    <h2 class="text-h5 mb-3">Upcoming plans</h2>
    <v-data-table :headers="headers" :items="planRows" :loading="loading" no-data-text="No upcoming capacity plans.">
      <template v-slot:[`item.starts_at`]="{ item }">{{ formatDateOnly(item.starts_at) }}</template>
      <template v-slot:[`item.ends_at`]="{ item }">{{ formatDateOnly(item.ends_at) }}</template>
      <template v-for="column in resourceColumns" v-slot:[`item.${column.value}`]="{ item }">
        <span :key="column.value">{{ item[column.value] == null ? "Unknown" : item[column.value] }}</span>
      </template>
      <template v-slot:[`item.auto_create`]="{ item }">{{ item.auto_create ? "Automatic" : "Manual" }}</template>
      <template v-slot:[`item.status`]="{ item }"
        >{{ item.status }}
        <div class="text-caption">{{ item.message }}</div></template
      >
      <template v-slot:[`item.actions`]="{ item }">
        <v-btn v-if="item.hostname" text small :to="`/clusters/${item.hostname}`">View cluster</v-btn>
        <v-btn v-if="item.can_edit" text small :disabled="saving" @click="editPlan(item)">Edit</v-btn>
        <v-btn v-if="item.can_cancel" text small color="error" @click="cancel(item)">Cancel</v-btn>
      </template>
    </v-data-table>
    <h2 class="text-h5 my-4">Future resource demand</h2>
    <v-data-table
      v-if="report.forecast"
      :headers="forecastHeaders"
      :items="forecastRows"
      item-key="starts_at"
      :items-per-page="-1"
      hide-default-footer
      no-data-text="No future resource demand."
    >
      <template v-slot:[`item.starts_at`]="{ item }">
        {{ formatDateOnly(item.starts_at) }} – {{ formatDateOnly(item.ends_at) }}
      </template>
      <template v-slot:[`item.shortages`]="{ item }">
        <span :class="Object.keys(item.shortages).length ? 'error--text' : ''">
          {{ Object.keys(item.shortages).length ? "Short by " + resources(item.shortages) : "Within estimated quota" }}
        </span>
      </template>
    </v-data-table>
    <confirm-dialog v-model="cancelDialog" title="Cancel capacity plan" @confirm="confirmCancel">
      {{ cancelMessage }}
    </confirm-dialog>
  </v-container>
</template>
<script>
import Repository from "@/repositories/Repository";
import ProjectRepository from "@/repositories/ProjectRepository";
import TemplateRepository from "@/repositories/TemplateRepository";
import ClusterEditor from "@/components/cluster/ClusterEditor";
import ConfirmDialog from "@/components/ui/ConfirmDialog";
export default {
  components: { ClusterEditor, ConfirmDialog },
  data: () => ({
    projects: [],
    projectId: null,
    report: {},
    specs: null,
    editingId: null,
    startsAt: "",
    endsAt: "",
    autoCreate: false,
    loading: false,
    saving: false,
    error: "",
    notice: "",
    previewReport: null,
    checkedPayload: null,
    cancelDialog: false,
    cancelItem: null,
    requestId: 0,
  }),
  computed: {
    resourceColumns() {
      const labels = {
        instance_count: "Instances",
        vcpus: "vCPUs",
        ram: "RAM (GiB)",
        gpus: "GPUs",
        volume_count: "Volumes",
        volume_size: "Storage (GiB)",
        ips: "Public IPs",
        gp2: "gp2 storage (GiB)",
        eips: "Elastic IPs",
      };
      const keys = new Set(["gpus"]);
      for (const row of [...(this.report.plans || []), ...(this.report.forecast?.segments || [])]) {
        Object.keys(row.demand || {}).forEach((key) => keys.add(key));
      }
      const ordered = [
        ...Object.keys(labels).filter((key) => keys.has(key)),
        ...[...keys].filter((key) => !(key in labels)).sort(),
      ];
      return ordered.map((key, index) => ({
        key,
        text: labels[key] || `${key} (vCPUs)`,
        value: `resource_${index}`,
        sortable: true,
        align: "end",
      }));
    },
    headers() {
      return [
        { text: "Cluster", value: "name" },
        { text: "Owner", value: "owner" },
        { text: "Start", value: "starts_at" },
        { text: "End", value: "ends_at" },
        ...this.resourceColumns,
        { text: "Creation", value: "auto_create" },
        { text: "Status", value: "status" },
        { text: "Actions", value: "actions", sortable: false },
      ];
    },
    planRows() {
      return (this.report.plans || []).map((plan) => ({
        ...plan,
        ...Object.fromEntries(
          this.resourceColumns.map((column) => [
            column.value,
            this.resourceValue(column.key, plan.demand?.[column.key] ?? (column.key === "gpus" ? null : 0)),
          ])
        ),
      }));
    },
    forecastHeaders() {
      return [
        { text: "Period (local dates)", value: "starts_at", sort: (a, b) => Date.parse(a) - Date.parse(b) },
        ...this.resourceColumns,
        { text: "Quota outlook", value: "shortages", sortable: false },
      ];
    },
    forecastRows() {
      return (this.report.forecast?.segments || []).map((segment) => ({
        ...segment,
        ...Object.fromEntries(
          this.resourceColumns.map((column) => [
            column.value,
            this.resourceValue(column.key, segment.demand?.[column.key] ?? 0),
          ])
        ),
      }));
    },
    cancelMessage() {
      const plan = this.cancelItem;
      let message = plan?.auto_create ? "Cancel this plan and its automatic start?" : "Cancel this plan?";
      if (plan && Date.parse(plan.starts_at) <= Date.now()) {
        message += " Existing cloud resources will remain running.";
      }
      return message;
    },
    periodRule() {
      return (
        (Date.parse(`${this.startsAt}T00:00:00`) > Date.now() &&
          Date.parse(`${this.endsAt}T00:00:00`) > Date.parse(`${this.startsAt}T00:00:00`)) ||
        "Choose a future start and a later end"
      );
    },
    conflicts() {
      return (this.previewReport?.segments || []).filter((s) => Object.keys(s.shortages).length);
    },
    formSnapshot() {
      return JSON.stringify([this.editingId, this.specs, this.startsAt, this.endsAt, this.autoCreate]);
    },
  },
  watch: {
    formSnapshot() {
      this.previewReport = null;
      this.checkedPayload = null;
    },
  },
  async created() {
    try {
      this.projects = (await ProjectRepository.getAll()).data;
      this.projectId =
        this.projects.find((p) => p.id === Number(this.$route.query.project))?.id || this.projects[0]?.id;
      await this.load();
    } catch (e) {
      this.showError(e);
    }
  },
  methods: {
    closeForm() {
      this.specs = null;
      this.editingId = null;
      this.startsAt = "";
      this.endsAt = "";
      this.autoCreate = false;
      this.previewReport = null;
      this.checkedPayload = null;
    },
    showError(e) {
      this.error = e.response?.data?.message || e.message || "Capacity planner request failed.";
    },
    formatDateOnly(value) {
      return new Date(value).toLocaleDateString();
    },
    formatDate(value) {
      return new Date(value).toLocaleString();
    },
    resourceValue(key, value) {
      return key === "ram" && value != null ? value / 1024 : value;
    },
    resources(values) {
      return (
        Object.entries(values || {})
          .filter(([key]) => key !== "gpus")
          .map(
            ([k, v]) =>
              `${k === "ram" ? "RAM (GiB)" : k.replace(/_/g, " ")}: ${
                v === null ? "unlimited" : this.resourceValue(k, v)
              }`
          )
          .join(", ") || "None"
      );
    },
    hasShortages(report) {
      return report.segments.some((s) => Object.keys(s.shortages).length);
    },
    localDate(value) {
      const date = new Date(value);
      return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(
        2,
        "0"
      )}`;
    },
    async editPlan(item) {
      const projectId = this.projectId;
      const requestId = ++this.requestId;
      this.specs = null;
      this.error = "";
      this.notice = "";
      this.saving = true;
      try {
        const { data: plan } = await Repository.get(`/projects/${projectId}/capacity/${item.id}`);
        if (requestId !== this.requestId) return;
        if (!plan.can_edit) throw new Error("This plan can no longer be edited. Refresh the planner.");
        this.editingId = plan.id;
        this.startsAt = this.localDate(plan.starts_at);
        this.endsAt = this.localDate(plan.ends_at);
        this.autoCreate = plan.auto_create;
        this.specs = plan.definition;
      } catch (e) {
        if (requestId === this.requestId) this.showError(e);
      } finally {
        this.saving = false;
      }
    },
    async load() {
      this.specs = null;
      this.editingId = null;
      if (!this.projectId) return;
      const id = ++this.requestId;
      this.loading = true;
      this.error = "";
      this.report = {};
      try {
        const response = await Repository.get(`/projects/${this.projectId}/capacity`);
        if (id === this.requestId) this.report = response.data;
      } catch (e) {
        if (id === this.requestId) this.showError(e);
      } finally {
        if (id === this.requestId) this.loading = false;
      }
    },
    async newPlan() {
      this.specs = null;
      this.editingId = null;
      try {
        this.specs = (await TemplateRepository.get("default")).data;
        this.previewReport = null;
        this.notice = "";
      } catch (e) {
        this.showError(e);
      }
    },
    async preview() {
      this.saving = true;
      this.error = "";
      const snapshot = this.formSnapshot;
      try {
        const payload = JSON.parse(
          JSON.stringify({
            definition: this.specs,
            starts_at: new Date(`${this.startsAt}T00:00:00`).toISOString(),
            ends_at: new Date(`${this.endsAt}T00:00:00`).toISOString(),
            auto_create: this.autoCreate,
          })
        );
        const path = `/projects/${this.projectId}/capacity${
          this.editingId === null ? "" : `/${this.editingId}`
        }/preview`;
        const response = await Repository.post(path, payload);
        if (snapshot === this.formSnapshot) {
          this.previewReport = response.data;
          this.checkedPayload = payload;
        }
      } catch (e) {
        this.showError(e);
      } finally {
        this.saving = false;
      }
    },
    async save() {
      if (!this.checkedPayload) return;
      this.saving = true;
      this.error = "";
      try {
        const response =
          this.editingId === null
            ? await Repository.post(`/projects/${this.projectId}/capacity`, this.checkedPayload)
            : await Repository.put(`/projects/${this.projectId}/capacity/${this.editingId}`, this.checkedPayload);
        this.notice = this.hasShortages(response.data.forecast)
          ? "Plan saved with quota conflicts. Review the forecast below."
          : "Capacity plan saved.";
        await this.load();
      } catch (e) {
        this.showError(e);
      } finally {
        this.saving = false;
      }
    },
    cancel(item) {
      this.cancelItem = item;
      this.cancelDialog = true;
    },
    async confirmCancel() {
      try {
        await Repository.delete(`/projects/${this.projectId}/capacity/${this.cancelItem.id}`);
        await this.load();
      } catch (e) {
        this.showError(e);
      }
    },
  },
};
</script>
