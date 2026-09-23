<template>
  <v-container>
    <h1 class="text-h4 mb-4">Project capacity planner</h1>
    <v-select v-model="projectId" :items="projects" item-text="name" item-value="id" label="Project" @change="load" />
    <v-alert v-if="error" type="error">{{ error }}</v-alert>
    <v-alert v-if="notice" type="success">{{ notice }}</v-alert>
    <v-alert type="info">
      Plans help your project coordinate resource usage. They do not reserve cloud capacity. OpenStack plans use the
      full project quotas; AWS forecasts account for current usage. Linked clusters are automatically torn down at the
      end of the period, deleting their resources and data.
    </v-alert>
    <v-btn color="primary" class="mr-2 mb-4" :disabled="!projectId || loading" @click="newPlan"
      >Plan resource usage</v-btn
    >
    <v-btn class="mb-4" :loading="loading" @click="load">Refresh</v-btn>
    <v-alert v-if="report.warning" type="warning">{{ report.warning }}</v-alert>
    <v-card v-if="specs" max-width="900" class="mx-auto mb-6">
      <v-card-title>New capacity plan</v-card-title>
      <v-card-text>
        <cluster-editor
          :specs="specs"
          :existing-cluster="false"
          planner-mode
          :auto-create="autoCreate"
          :project-ids="[projectId]"
          submit-label="Check planned capacity"
          :submit-disabled="saving"
          @apply="preview"
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
        <v-btn v-if="previewReport" color="primary" :loading="saving" @click="save">Save capacity plan</v-btn>
        <v-btn text @click="specs = null">Close form</v-btn>
      </v-card-text>
    </v-card>
    <h2 class="text-h5 mb-3">Upcoming plans</h2>
    <v-data-table
      :headers="headers"
      :items="report.plans || []"
      :loading="loading"
      no-data-text="No upcoming capacity plans."
    >
      <template v-slot:[`item.starts_at`]="{ item }">{{ formatDateOnly(item.starts_at) }}</template>
      <template v-slot:[`item.ends_at`]="{ item }">{{ formatDateOnly(item.ends_at) }}</template>
      <template v-slot:[`item.gpus`]="{ item }">{{ item.demand.gpus == null ? "Unknown" : item.demand.gpus }}</template>
      <template v-slot:[`item.demand`]="{ item }">{{ resources(item.demand) }}</template>
      <template v-slot:[`item.auto_create`]="{ item }">{{ item.auto_create ? "Automatic" : "Manual" }}</template>
      <template v-slot:[`item.status`]="{ item }"
        >{{ item.status }}
        <div class="text-caption">{{ item.message }}</div></template
      >
      <template v-slot:[`item.actions`]="{ item }">
        <v-btn v-if="item.hostname" text small :to="`/clusters/${item.hostname}`">View cluster</v-btn>
        <v-btn
          v-if="item.can_manage && item.status === 'planned' && !item.auto_create"
          text
          small
          :to="creationLink(item)"
          >Create manually</v-btn
        >
        <v-btn v-if="item.can_cancel" text small color="error" @click="cancel(item)">Cancel plan</v-btn>
      </template>
    </v-data-table>
    <h2 class="text-h5 my-4">Future resource demand</h2>
    <p v-if="report.forecast">
      {{
        report.forecast.quota_basis === "project_total"
          ? "Total project capacity"
          : "Additional capacity available now"
      }}: {{ resources(report.forecast.available) }}. RAM is in MiB; storage is in GiB; AWS instance pools are in vCPUs.
      GPU counts are reported even without a GPU quota.
    </p>
    <v-simple-table v-if="report.forecast">
      <thead>
        <tr>
          <th>Period (local dates)</th>
          <th>Planned demand</th>
          <th>GPUs</th>
          <th>Quota outlook</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(segment, index) in report.forecast.segments" :key="index">
          <td>{{ formatDateOnly(segment.starts_at) }} – {{ formatDateOnly(segment.ends_at) }}</td>
          <td>{{ resources(segment.demand) }}</td>
          <td>{{ segment.demand.gpus || 0 }}</td>
          <td :class="Object.keys(segment.shortages).length ? 'error--text' : ''">
            {{
              Object.keys(segment.shortages).length
                ? "Short by " + resources(segment.shortages)
                : "Within estimated quota"
            }}
          </td>
        </tr>
      </tbody>
    </v-simple-table>
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
    headers: [
      { text: "Cluster", value: "name" },
      { text: "Owner", value: "owner" },
      { text: "Start", value: "starts_at" },
      { text: "End", value: "ends_at" },
      { text: "Resources", value: "demand", sortable: false },
      { text: "GPUs", value: "gpus", sortable: false },
      { text: "Creation", value: "auto_create" },
      { text: "Status", value: "status" },
      { text: "Actions", value: "actions", sortable: false },
    ],
  }),
  computed: {
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
      return JSON.stringify([this.specs, this.startsAt, this.endsAt, this.autoCreate]);
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
    showError(e) {
      this.error = e.response?.data?.message || e.message || "Capacity planner request failed.";
    },
    formatDateOnly(value) {
      return new Date(value).toLocaleDateString();
    },
    formatDate(value) {
      return new Date(value).toLocaleString();
    },
    resources(values) {
      return (
        Object.entries(values || {})
          .filter(([key]) => key !== "gpus")
          .map(([k, v]) => `${k.replace(/_/g, " ")}: ${v === null ? "unlimited" : v}`)
          .join(", ") || "None"
      );
    },
    hasShortages(report) {
      return report.segments.some((s) => Object.keys(s.shortages).length);
    },
    creationLink(item) {
      return { path: "/create-cluster", query: { capacityProject: this.projectId, capacityPlan: item.id } };
    },
    async load() {
      this.specs = null;
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
        const response = await Repository.post(`/projects/${this.projectId}/capacity/preview`, payload);
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
        const response = await Repository.post(`/projects/${this.projectId}/capacity`, this.checkedPayload);
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
