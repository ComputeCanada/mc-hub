import { mount, flushPromises } from "@vue/test-utils";
import { createAppVuetify } from "@/plugins/vuetify";
import Benchmarks from "@/views/Benchmarks";
import BenchmarkEditor from "@/views/BenchmarkEditor";
import Repository from "@/repositories/Repository";
import UserRepository from "@/repositories/UserRepository";
import ProjectRepository from "@/repositories/ProjectRepository";
import TemplateRepository from "@/repositories/TemplateRepository";
import Resources from "@/repositories/AvailableResourcesRepository";

jest.mock("@/repositories/Repository", () => ({
  get: jest.fn(),
  post: jest.fn(),
  put: jest.fn(),
  patch: jest.fn(),
  delete: jest.fn(),
}));
jest.mock("@/repositories/UserRepository", () => ({ getCurrent: jest.fn() }));
jest.mock("@/repositories/ProjectRepository", () => ({ getAll: jest.fn() }));
jest.mock("@/repositories/TemplateRepository", () => ({ get: jest.fn() }));
jest.mock("@/repositories/AvailableResourcesRepository", () => ({ getCloud: jest.fn() }));
const projects = [
  { id: 11, name: "Research" },
  { id: 22, name: "Teaching" },
];
const benchmark = (id = "bench-1") => ({
  id,
  project_id: 11,
  name: id,
  frequency: "daily",
  success_criterion: "healthy",
  timeout_minutes: 120,
  enabled: true,
  archived: false,
  identity_locked: true,
  setup_status: "ready",
  next_run_at: "2027-01-01T12:00:00Z",
  configuration: specs(),
});
function result(id = "bench-1") {
  return {
    benchmark: benchmark(id),
    total_runs: 2,
    default_comparison_group: "healthy",
    comparison_groups: ["healthy", "build_completed"].map((criterion) => ({
      id: criterion,
      commit_sha: "abcdef0123456789",
      repository: "org/repo",
      success_criterion: criterion,
      total_runs: 1,
      success_rate: 1,
      timing: { average_seconds: 120, median_seconds: 120, p95_seconds: 120 },
    })),
    runs: ["healthy", "build_completed"].map((criterion, index) => ({
      id: criterion,
      requested_at: `2027-01-0${index + 1}T12:00:00Z`,
      measurement_started_at: `2027-01-0${index + 1}T12:01:00Z`,
      outcome: "successful",
      phase: "cleanup",
      cleanup_error: "Retry cleanup",
      error: "Diagnostic detail",
      hostname: "bench.example.org",
      configuration: { cluster_name: "saved-specs" },
      commit_sha: "abcdef0123456789",
      repository: "org/repo",
      success_criterion: criterion,
      duration_seconds: 120,
    })),
  };
}
const specs = () => ({
  cloud: { id: 11, name: "Research" },
  cluster_name: "test",
  domain: "example.org",
  mc_version: "14",
  image: "image",
  instances: { node: { count: 1, type: "p1", tags: ["node"] } },
  volumes: { nfs: {} },
  public_keys: [],
  guest_passwd: "password",
  nb_users: 1,
});
let wrapper, host, warn, router;
beforeEach(() => {
  jest.clearAllMocks();
  router = { push: jest.fn() };
  UserRepository.getCurrent.mockResolvedValue({ data: { is_admin: true, public_keys: [], default_project_id: 11 } });
  ProjectRepository.getAll.mockResolvedValue({ data: projects });
  TemplateRepository.get.mockImplementation(async () => ({ data: specs() }));
  Resources.getCloud.mockResolvedValue({
    data: {
      provider: "openstack",
      quotas: Object.fromEntries(
        ["instance_count", "ram", "vcpus", "volume_count", "volume_size", "ips"].map((key) => [key, { max: 10000 }])
      ),
      possible_resources: {
        domain: ["example.org"],
        mc_version: ["14"],
        image: ["image"],
        types: ["p1"],
        tag_types: {},
      },
      resource_details: {
        instance_types: [{ name: "p1", ram: 1024, vcpus: 1, required_volume_count: 0, required_volume_size: 0 }],
      },
    },
  });
  Repository.get.mockImplementation(async (path) => ({
    data:
      path === "/benchmarks"
        ? { projects, benchmarks: [benchmark(), benchmark("bench-2")] }
        : result(path.split("/").pop()),
  }));
  Repository.patch.mockResolvedValue({});
  Repository.post.mockResolvedValue({ data: { id: "bench-1" } });
  Repository.put.mockResolvedValue({ data: { id: "bench-1" } });
  Repository.delete.mockResolvedValue({});
  host = document.createElement("div");
  document.body.append(host);
  warn = jest.spyOn(console, "warn");
});
afterEach(() => {
  if (wrapper?.exists()) wrapper.unmount();
  host.remove();
  document.querySelectorAll(".v-overlay-container").forEach((node) => node.remove());
  expect(warn).not.toHaveBeenCalled();
  jest.restoreAllMocks();
});
async function render(component, props = {}) {
  wrapper = mount(component, {
    props,
    attachTo: host,
    global: {
      plugins: [createAppVuetify()],
      mocks: {
        $route: { query: { benchmark: "bench-1" } },
        $router: router,
        $enableUnloadConfirmation: jest.fn(),
        $disableUnloadConfirmation: jest.fn(),
      },
    },
  });
  await flushPromises();
}
function field(label) {
  return wrapper.findAllComponents({ name: "VTextField" }).find((input) => input.props("label") === label);
}
function select(label) {
  return wrapper.findAllComponents({ name: "VSelect" }).find((input) => input.props("label") === label);
}
async function click(text) {
  const button = [...document.querySelectorAll("button")].find((node) => node.textContent.trim() === text);
  expect(button).toBeDefined();
  expect(button.disabled).toBe(false);
  button.click();
  await flushPromises();
}
function deferred() {
  let resolve;
  const promise = new Promise((done) => {
    resolve = done;
  });
  return { promise, resolve };
}

test("dashboard renders sorted run history, expands diagnostics, and changes comparison groups", async () => {
  await render(Benchmarks);
  const table = wrapper.get("table");
  expect(table.findAll("th").map((cell) => cell.text())).toContain("Success criterion");
  expect(table.findAll("tbody tr")[0].text()).toContain("2027-01-02");
  await table.findAll("tbody tr")[0].get("button").trigger("click");
  expect(table.text()).toContain("Diagnostic detail");
  expect(table.text()).toContain("Retry cleanup");
  expect(table.get("pre").text()).toContain("saved-specs");
  expect(wrapper.text()).toContain("Apply to healthy over time");
  await select("Commit and success criterion").setValue("build_completed");
  expect(wrapper.text()).toContain("Terraform apply duration over time");
  expect(wrapper.findAll("svg circle")).toHaveLength(1);
  expect(table.text()).toContain("2027-01-01");
  await select("Benchmark").setValue("bench-2");
  await flushPromises();
  expect(Repository.get).toHaveBeenLastCalledWith("/benchmarks/bench-2");
  expect(wrapper.get("h2").text()).toBe("bench-2");
});

test("dashboard buttons run, pause, and archive only after confirmation", async () => {
  await render(Benchmarks);
  await click("Run now");
  expect(Repository.post).toHaveBeenCalledWith("/benchmarks/bench-1/run");
  await click("Pause schedule");
  expect(Repository.patch).toHaveBeenCalledWith("/benchmarks/bench-1", { enabled: false });
  const confirm = jest.spyOn(window, "confirm").mockReturnValueOnce(false).mockReturnValueOnce(true);
  await click("Archive");
  expect(Repository.delete).not.toHaveBeenCalled();
  await click("Archive");
  expect(confirm).toHaveBeenCalledTimes(2);
  expect(Repository.delete).toHaveBeenCalledWith("/benchmarks/bench-1");
});

test("project and archived filters choose only visible benchmarks", async () => {
  Repository.get.mockImplementation(async (path) => ({
    data:
      path === "/benchmarks"
        ? {
            projects,
            benchmarks: [benchmark(), { ...benchmark("archived"), project_id: 22, archived: true }],
          }
        : { ...result("archived"), benchmark: { ...benchmark("archived"), archived: true } },
  }));
  await render(Benchmarks);
  await select("Project").setValue(22);
  await flushPromises();
  expect(wrapper.find("table").exists()).toBe(false);
  expect(wrapper.text()).toContain("No benchmarks yet");
  await wrapper.findComponent({ name: "VSwitch" }).get("input").setValue(true);
  await flushPromises();
  expect(Repository.get).toHaveBeenLastCalledWith("/benchmarks/archived");
  expect(wrapper.find("table").exists()).toBe(true);
  expect(wrapper.findAll("button").some((button) => button.text() === "Run now")).toBe(false);
});

test("editor saves the real form's criterion, schedule, timeout and UTC timestamp", async () => {
  await render(BenchmarkEditor, { id: "bench-1" });
  await field("Benchmark name").get("input").setValue("Updated benchmark");
  await select("Success criterion").setValue("build_completed");
  await select("Frequency").setValue("weekly");
  await field("Maximum run time (minutes)").get("input").setValue("240");
  await field("Next scheduled run (UTC)").get("input").setValue("2027-03-02T10:15");
  await flushPromises();
  await click("Save benchmark");
  expect(Repository.put).toHaveBeenCalledWith(
    "/benchmarks/bench-1",
    expect.objectContaining({
      name: "Updated benchmark",
      success_criterion: "build_completed",
      frequency: "weekly",
      timeout_minutes: 240,
      next_run_at: "2027-03-02T10:15:00Z",
      project_id: 11,
    })
  );
  expect(router.push).toHaveBeenCalledWith({ path: "/benchmarks", query: { benchmark: "bench-1" } });
});

test("an editor save finishing after unmount does not navigate", async () => {
  await render(BenchmarkEditor, { id: "bench-1" });
  const pending = deferred();
  Repository.put.mockReturnValueOnce(pending.promise);
  await click("Save benchmark");
  wrapper.unmount();
  pending.resolve({ data: { id: "bench-1" } });
  await flushPromises();
  expect(router.push).not.toHaveBeenCalled();
});

test("new benchmark setup failure retries the created ID through the real form", async () => {
  await render(BenchmarkEditor);
  await field("Benchmark name").get("input").setValue("New benchmark");
  await flushPromises();
  Repository.post.mockRejectedValueOnce({
    response: {
      data: {
        message: "Setup failed; save to retry",
        benchmark: { ...benchmark(), setup_status: "failed" },
      },
    },
  });
  await click("Save benchmark");
  expect(wrapper.text()).toContain("Setup failed; save to retry");
  expect(router.push).not.toHaveBeenCalled();
  expect(field("Cluster name").props("readonly")).toBe(true);
  await click("Save benchmark");
  expect(Repository.post).toHaveBeenCalledTimes(1);
  expect(Repository.put).toHaveBeenCalledWith(
    "/benchmarks/bench-1",
    expect.objectContaining({ name: "New benchmark" })
  );
  expect(router.push).toHaveBeenCalled();
});
