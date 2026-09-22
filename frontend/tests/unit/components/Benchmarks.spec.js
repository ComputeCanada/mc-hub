import Vue from "vue";
import Vuetify from "vuetify";
import { shallowMount } from "@vue/test-utils";
import Benchmarks from "@/views/Benchmarks";
import BenchmarkEditor from "@/views/BenchmarkEditor";
import ClusterEditor from "@/components/cluster/ClusterEditor";
import Repository from "@/repositories/Repository";
import TemplateRepository from "@/repositories/TemplateRepository";

Vue.use(Vuetify);
jest.mock("@/repositories/Repository", () => ({
  get: jest.fn(),
  post: jest.fn(),
  put: jest.fn(),
  patch: jest.fn(),
  delete: jest.fn(),
}));
jest.mock("@/repositories/TemplateRepository", () => ({ get: jest.fn() }));
const flush = () => new Promise(jest.requireActual("timers").setImmediate);
const benchmark = {
  id: "bench-1",
  project_id: 1,
  name: "Test",
  frequency: "daily",
  success_criterion: "healthy",
  timeout_minutes: 120,
  enabled: true,
  archived: false,
  identity_locked: true,
  setup_status: "ready",
  setup_error: null,
  next_run_at: "2027-01-01T12:00:00Z",
  configuration: { cloud: { id: 1 }, cluster_name: "specs" },
};
const result = {
  benchmark,
  runs: [],
  total_runs: 0,
  comparison_groups: [],
  default_comparison_group: null,
  unassigned_runs: 0,
  timing: { average_seconds: null, median_seconds: null, p95_seconds: null },
  success_rate: null,
};
const mounts = [];
function mount(component, options = {}) {
  const wrapper = shallowMount(component, {
    mocks: {
      $route: { query: { benchmark: "bench-1" } },
      $router: { push: jest.fn() },
      $disableUnloadConfirmation: jest.fn(),
    },
    ...options,
  });
  mounts.push(wrapper);
  return wrapper;
}
beforeEach(() => {
  jest.clearAllMocks();
  Repository.get.mockImplementation((path) =>
    Promise.resolve({
      data: JSON.parse(
        JSON.stringify(
          path === "/benchmarks" ? { projects: [{ id: 1, name: "Research" }], benchmarks: [benchmark] } : result
        )
      ),
    })
  );
  TemplateRepository.get.mockResolvedValue({ data: { cloud: {}, cluster_name: "" } });
});
afterEach(() => mounts.splice(0).forEach((w) => w.destroy()));

test("dashboard compares one commit and criterion at a time and retains all history", async () => {
  const wrapper = mount(Benchmarks);
  await flush();
  expect(wrapper.text()).toContain("No successful timed runs for this group");
  const group = (id, commit, criterion, seconds) => ({
    id,
    commit_sha: commit,
    success_criterion: criterion,
    repository: "org/repo",
    total_runs: 1,
    timing: { average_seconds: seconds, median_seconds: seconds, p95_seconds: seconds },
    success_rate: 1,
  });
  await wrapper.setData({
    comparisonGroup: "new-healthy",
    report: {
      ...result,
      benchmark: { ...benchmark },
      comparison_groups: [
        group("new-healthy", "new-sha", "healthy", 120),
        group("old-healthy", "old-sha", "healthy", 600),
        group("new-build", "new-sha", "build_completed", 60),
      ],
      unassigned_runs: 1,
      runs: [
        {
          id: "good",
          commit_sha: "new-sha",
          repository: "org/repo",
          success_criterion: "healthy",
          outcome: "successful",
          applied_at: "2027-01-01T12:00:00Z",
          measurement_started_at: "2027-01-01T12:00:00Z",
          duration_seconds: 120,
        },
        {
          id: "build",
          commit_sha: "new-sha",
          repository: "org/repo",
          success_criterion: "build_completed",
          outcome: "successful",
          applied_at: null,
          apply_started_at: "2027-01-01T12:01:00Z",
          measurement_started_at: "2027-01-01T12:01:00Z",
          duration_seconds: 60,
        },
        {
          id: "old",
          commit_sha: "old-sha",
          repository: "org/repo",
          success_criterion: "healthy",
          outcome: "successful",
          duration_seconds: 600,
          applied_at: "2027-01-01T11:00:00Z",
          measurement_started_at: "2027-01-01T11:00:00Z",
        },
        {
          id: "legacy-build",
          commit_sha: "new-sha",
          repository: "org/repo",
          success_criterion: "build_completed",
          outcome: "successful",
          applied_at: "2027-01-01T11:00:00Z",
          target_reached_at: "2027-01-01T11:16:00Z",
          measurement_started_at: null,
          apply_started_at: null,
          duration_seconds: null,
        },
        {
          id: "failed",
          commit_sha: "new-sha",
          repository: "org/repo",
          success_criterion: "healthy",
          outcome: "failed",
          duration_seconds: null,
        },
        {
          id: "unknown",
          commit_sha: null,
          repository: "org/repo",
          success_criterion: "healthy",
          outcome: "successful",
          duration_seconds: 900,
        },
      ],
    },
  });
  expect(wrapper.vm.points.map((p) => p.id)).toEqual(["good"]);
  expect(wrapper.vm.cards[0].value).toBe("2.0 min");
  expect(wrapper.text()).toContain("1 runs have no recorded commit");
  expect(wrapper.find("v-data-table-stub").attributes("items")).toBeDefined();
  expect(wrapper.find('svg[aria-label="Benchmark deployment duration trend"]').exists()).toBe(true);
  expect(wrapper.text()).toContain("Apply to healthy over time");
  await wrapper.setData({ comparisonGroup: "old-healthy" });
  expect(wrapper.vm.points.map((p) => p.id)).toEqual(["old"]);
  expect(wrapper.vm.cards[0].value).toBe("10.0 min");
  await wrapper.setData({ comparisonGroup: "new-build" });
  expect(wrapper.vm.points.map((p) => p.id)).toEqual(["build"]);
  expect(wrapper.text()).toContain("Terraform apply duration over time");
  expect(wrapper.text()).toContain("Queue time and worker polling delays are excluded");
  expect(wrapper.vm.points[0].measurement_started_at).toBe("2027-01-01T12:01:00Z");
  expect(wrapper.vm.points[0].x).toBe(45);
  expect(wrapper.vm.report.runs).toHaveLength(6);
});

test("refresh preserves a selected historical group and changing benchmarks resets it", async () => {
  const groups = ["latest", "historical"].map((id) => ({
    id,
    commit_sha: id,
    success_criterion: "healthy",
    repository: "org/repo",
    total_runs: 1,
    timing: result.timing,
    success_rate: null,
  }));
  const response = { ...result, comparison_groups: groups, default_comparison_group: "latest" };
  Repository.get.mockImplementation((path) =>
    Promise.resolve({ data: path === "/benchmarks" ? { projects: [{ id: 1 }], benchmarks: [benchmark] } : response })
  );
  const wrapper = mount(Benchmarks);
  await flush();
  expect(wrapper.vm.comparisonGroup).toBe("latest");
  await wrapper.setData({ comparisonGroup: "historical" });
  await wrapper.vm.loadReport();
  expect(wrapper.vm.comparisonGroup).toBe("historical");
  Repository.get.mockResolvedValue({ data: { ...response, benchmark: { ...benchmark, id: "bench-2" } } });
  await wrapper.setData({ selected: "bench-2" });
  await wrapper.vm.loadReport();
  expect(wrapper.vm.comparisonGroup).toBe("latest");
});

test("Run now shows overlap rejection; pause uses the schedule-only API", async () => {
  const wrapper = mount(Benchmarks);
  await flush();
  Repository.post.mockRejectedValue({ response: { data: { message: "Wait for cleanup" } } });
  await wrapper.vm.runNow();
  expect(Repository.post).toHaveBeenCalledWith("/benchmarks/bench-1/run");
  expect(wrapper.text()).toContain("Wait for cleanup");
  Repository.patch.mockResolvedValue({});
  await wrapper.vm.toggleEnabled();
  expect(Repository.patch).toHaveBeenCalledWith("/benchmarks/bench-1", { enabled: false });
});

test("incomplete setup explains the retry and disables Run now", async () => {
  const wrapper = mount(Benchmarks);
  await flush();
  await wrapper.setData({
    report: { ...result, benchmark: { ...benchmark, setup_status: "failed", setup_error: "Setup failed" } },
  });
  expect(wrapper.text()).toContain("Edit and save this benchmark to finish setup");
  const runNow = wrapper.findAll("v-btn-stub").wrappers.find((button) => button.text() === "Run now");
  expect(runNow.attributes("disabled")).toBe("true");
});

test("failed first save retries the same benchmark and preserves its identity", async () => {
  const wrapper = mount(BenchmarkEditor);
  await flush();
  await wrapper.setData({ specs: { ...benchmark.configuration }, name: "Test" });
  Repository.post.mockRejectedValueOnce({
    response: {
      data: { message: "Setup failed. Save again to retry.", benchmark: { ...benchmark, setup_status: "failed" } },
    },
  });
  await wrapper.vm.save();
  expect(wrapper.text()).toContain("Setup failed. Save again to retry.");
  expect(wrapper.findComponent(ClusterEditor).props("identityLocked")).toBe(true);
  expect(wrapper.findComponent(ClusterEditor).props("projectIds")).toEqual([1]);
  expect(wrapper.vm.$router.push).not.toHaveBeenCalled();
  Repository.put.mockResolvedValueOnce({ data: benchmark });
  await wrapper.vm.save();
  expect(Repository.post).toHaveBeenCalledTimes(1);
  expect(Repository.put).toHaveBeenCalledWith("/benchmarks/bench-1", expect.objectContaining({ name: "Test" }));
  expect(wrapper.vm.$router.push).toHaveBeenCalledWith({ path: "/benchmarks", query: { benchmark: "bench-1" } });
});

test("editor reuses cluster form with project restriction and preserves saved specs", async () => {
  const wrapper = mount(BenchmarkEditor, { propsData: { id: "bench-1" } });
  await flush();
  const editor = wrapper.findComponent(ClusterEditor);
  expect(editor.props("benchmarkMode")).toBe(true);
  expect(editor.props("preserveSpecs")).toBe(true);
  expect(editor.props("identityLocked")).toBe(true);
  expect(editor.props("projectIds")).toEqual([1]);
  expect(editor.props("specs").cluster_name).toBe("specs");
  Repository.put.mockResolvedValue({ data: benchmark });
  await wrapper.vm.save();
  expect(Repository.put).toHaveBeenCalledWith(
    "/benchmarks/bench-1",
    expect.objectContaining({
      next_run_at: "2027-01-01T12:00:00Z",
      frequency: "daily",
      success_criterion: "healthy",
      project_id: 1,
    })
  );
});

test("editor loads and saves the selected success criterion", async () => {
  Repository.get.mockImplementation((path) =>
    Promise.resolve({
      data:
        path === "/benchmarks"
          ? { projects: [{ id: 1, name: "Research" }], benchmarks: [benchmark] }
          : { ...result, benchmark: { ...benchmark, success_criterion: "build_completed" } },
    })
  );
  const wrapper = mount(BenchmarkEditor, { propsData: { id: "bench-1" } });
  await flush();
  expect(wrapper.vm.successCriterion).toBe("build_completed");
  Repository.put.mockResolvedValue({ data: benchmark });
  await wrapper.vm.save();
  expect(Repository.put).toHaveBeenLastCalledWith(
    "/benchmarks/bench-1",
    expect.objectContaining({ success_criterion: "build_completed" })
  );
  await wrapper.setData({ successCriterion: "healthy" });
  await wrapper.vm.save();
  expect(Repository.put).toHaveBeenLastCalledWith(
    "/benchmarks/bench-1",
    expect.objectContaining({ success_criterion: "healthy" })
  );
});

test("no project admin access means no benchmark form", async () => {
  Repository.get.mockResolvedValue({ data: { projects: [], benchmarks: [] } });
  const wrapper = mount(BenchmarkEditor);
  await flush();
  expect(wrapper.findComponent(ClusterEditor).exists()).toBe(false);
  expect(wrapper.text()).toContain("project administrator role");
});
