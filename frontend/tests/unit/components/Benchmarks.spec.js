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

test("dashboard displays empty measurements and excludes failures from timing chart", async () => {
  const wrapper = mount(Benchmarks);
  await flush();
  expect(wrapper.text()).toContain("No successful timed runs yet");
  await wrapper.setData({
    report: {
      ...result,
      benchmark: { ...benchmark },
      runs: [
        {
          id: "good",
          success_criterion: "healthy",
          outcome: "successful",
          applied_at: "2027-01-01T12:00:00Z",
          duration_seconds: 120,
        },
        {
          id: "build",
          success_criterion: "build_completed",
          outcome: "successful",
          applied_at: "2027-01-01T12:00:00Z",
          duration_seconds: 60,
        },
        { id: "failed", outcome: "failed", duration_seconds: null },
      ],
    },
  });
  expect(wrapper.vm.points.map((p) => p.id)).toEqual(["good"]);
  expect(wrapper.find('svg[aria-label="Benchmark deployment duration trend"]').exists()).toBe(true);
  expect(wrapper.text()).toContain("Apply to healthy over time");
  await wrapper.setData({
    report: { ...wrapper.vm.report, benchmark: { ...benchmark, success_criterion: "build_completed" } },
  });
  expect(wrapper.vm.points.map((p) => p.id)).toEqual(["build"]);
  expect(wrapper.text()).toContain("Apply to build completed over time");
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
