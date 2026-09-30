import { mount, flushPromises } from "@vue/test-utils";
import { createAppVuetify } from "@/plugins/vuetify";
import CreateCluster from "@/views/CreateCluster";
import Usage from "@/views/Usage";
import CapacityPlanner from "@/views/CapacityPlanner";
import Repository from "@/repositories/Repository";
import UserRepository from "@/repositories/UserRepository";
import ProjectRepository from "@/repositories/ProjectRepository";
import TemplateRepository from "@/repositories/TemplateRepository";
import Resources from "@/repositories/AvailableResourcesRepository";

jest.mock("@/repositories/Repository", () => ({ get: jest.fn(), post: jest.fn(), put: jest.fn(), delete: jest.fn() }));
jest.mock("@/repositories/UserRepository", () => ({ getCurrent: jest.fn() }));
jest.mock("@/repositories/ProjectRepository", () => ({ getAll: jest.fn() }));
jest.mock("@/repositories/TemplateRepository", () => ({ get: jest.fn() }));
jest.mock("@/repositories/AvailableResourcesRepository", () => ({ getCloud: jest.fn() }));
const durations = { count: 0, average_seconds: null, median_seconds: null, p95_seconds: null };
const projects = [
  { id: 11, name: "Research" },
  { id: 22, name: "Teaching" },
];
function usage(page = 1) {
  return {
    projects,
    page,
    summary: { unique_creators: 5 },
    months: [
      { month: "2026-01", successful_deployments: 10 },
      { month: "2026-02", successful_deployments: 2 },
    ],
    attempts: [{ id: page, hostname: `cluster-${page}`, duration_seconds: 120, applied_at: "2026-01-01T00:00:00Z" }],
    attempt_count: 26,
    apply_to_healthy: durations,
    completed_lifetime: durations,
    ongoing_age: durations,
    last_poll_at: null,
  };
}
function plan(id, gpus, extra = {}) {
  return {
    id,
    name: `plan-${id}`,
    owner: "alice",
    starts_at: "2999-01-01T00:00:00Z",
    ends_at: "2999-01-02T00:00:00Z",
    demand: { gpus, ram: 2048 },
    status: "planned",
    ...extra,
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
let wrapper, host, warn;
beforeEach(() => {
  jest.clearAllMocks();
  UserRepository.getCurrent.mockResolvedValue({ data: { is_admin: true, public_keys: [], default_project_id: 11 } });
  ProjectRepository.getAll.mockResolvedValue({ data: projects });
  TemplateRepository.get.mockImplementation(async () => ({ data: specs() }));
  Resources.getCloud.mockResolvedValue({
    data: {
      provider: "openstack",
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
  Repository.get.mockResolvedValue({ data: usage() });
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
async function render(component, query = {}) {
  wrapper = mount(component, {
    attachTo: host,
    global: {
      plugins: [createAppVuetify()],
      mocks: {
        $route: { query },
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

test("Usage renders headings, descending months, progress and formatted history", async () => {
  await render(Usage);
  const tables = wrapper.findAll("table");
  expect(tables[0].findAll("th").map((cell) => cell.text())).toContain("Successful deployments");
  expect(tables[0].findAll("tbody tr").map((row) => row.get("td").text())).toEqual(["2026-02", "2026-01"]);
  expect(tables[0].findAll('[role="progressbar"]').map((bar) => bar.attributes("aria-valuenow"))).toEqual([
    "20",
    "100",
  ]);
  expect(tables[1].text()).toContain("cluster-1");
  expect(tables[1].text()).toContain("2.0 min");
  expect(tables[1].text()).toContain("Unknown");
  expect(wrapper.text()).toContain("Background observations are overdue");
});

test("Usage filters send IDs and date strings, and pagination fetches the next server page", async () => {
  await render(Usage);
  expect(select("All projects").props("itemTitle")).toBe("name");
  await field("From (UTC)").get("input").setValue("2026-01-01");
  await field("Through (UTC)").get("input").setValue("2026-02-28");
  await select("All projects").setValue(22);
  await click("Update");
  expect(Repository.get).toHaveBeenLastCalledWith("/usage", {
    params: { start: "2026-01-01", end: "2026-02-28", project: 22, page: 1 },
  });
  Repository.get.mockResolvedValueOnce({ data: usage(2) });
  await wrapper.findAllComponents({ name: "VPagination" }).at(-1).get(".v-pagination__next button").trigger("click");
  await flushPromises();
  expect(Repository.get).toHaveBeenLastCalledWith("/usage", {
    params: expect.objectContaining({ project: 22, page: 2 }),
  });
  expect(wrapper.findAll("table")[1].text()).toContain("cluster-2");
  await select("All projects").setValue(null);
  await click("Update");
  expect(Repository.get).toHaveBeenLastCalledWith("/usage", {
    params: expect.objectContaining({ project: undefined, page: 1 }),
  });
});

test("Usage denies access before loading any report", async () => {
  UserRepository.getCurrent.mockResolvedValueOnce({ data: { is_admin: false } });
  await render(Usage);
  expect(Repository.get).not.toHaveBeenCalled();
  expect(wrapper.find("table").exists()).toBe(false);
  expect(wrapper.text()).toContain("Only hub admins");
});

test("Usage ignores an older request and responses after unmount", async () => {
  await render(Usage);
  const old = deferred();
  Repository.get.mockReturnValueOnce(old.promise).mockResolvedValueOnce({ data: usage(2) });
  const first = wrapper.vm.load(1);
  await wrapper.vm.load(2);
  old.resolve({ data: usage(1) });
  await first;
  expect(wrapper.findAll("table")[1].text()).toContain("cluster-2");
  const pending = deferred();
  Repository.get.mockReturnValueOnce(pending.promise);
  const vm = wrapper.vm;
  const request = vm.load(1);
  wrapper.unmount();
  pending.resolve({ data: usage(1) });
  await request;
  expect(vm.report.page).toBe(2);
});

test("planner renders resource cells and sorts GPU totals numerically through column headers", async () => {
  Repository.get.mockResolvedValue({
    data: { plans: [plan(1, 10), plan(2, 2), plan(3, null)], forecast: { segments: [] } },
  });
  await render(CapacityPlanner);
  const table = wrapper.get("table");
  const headers = table.findAll("th");
  expect(headers.map((cell) => cell.text())).toContain("RAM (GiB)");
  expect(table.text()).toContain("Unknown");
  await headers.find((cell) => cell.text() === "GPUs").trigger("click");
  expect(table.findAll("tbody tr").map((row) => row.get("td").text())).toEqual(["plan-3", "plan-2", "plan-1"]);
  expect(table.findAll("tbody tr")[0].find("button").exists()).toBe(false);
});

test("planner project selection loads the selected ID and ignores the previous project response", async () => {
  Repository.get.mockResolvedValue({ data: { plans: [plan(1, 1)] } });
  await render(CapacityPlanner, { project: "22" });
  expect(Repository.get).toHaveBeenLastCalledWith("/projects/22/capacity");
  const pending = deferred();
  Repository.get.mockReturnValueOnce(pending.promise);
  await select("Project").setValue(11);
  expect(Repository.get).toHaveBeenLastCalledWith("/projects/11/capacity");
  Repository.get.mockResolvedValueOnce({ data: { plans: [plan(22, 2)] } });
  await select("Project").setValue(22);
  await flushPromises();
  pending.resolve({ data: { plans: [plan(11, 1)] } });
  await flushPromises();
  expect(wrapper.get("table").text()).toContain("plan-22");
  expect(wrapper.get("table").text()).not.toContain("plan-11");
});

test("planner cancellation uses the real confirmation dialog and refreshes after confirmation", async () => {
  Repository.get.mockResolvedValue({ data: { plans: [plan(42, 2, { can_cancel: true, auto_create: true })] } });
  await render(CapacityPlanner);
  await click("Cancel");
  expect(document.body.textContent).toContain("Cancel this plan and its automatic start?");
  await click("No");
  expect(Repository.delete).not.toHaveBeenCalled();
  await click("Cancel");
  Repository.get.mockResolvedValueOnce({ data: { plans: [] } });
  await click("Yes");
  expect(Repository.delete).toHaveBeenCalledWith("/projects/11/capacity/42");
  expect(wrapper.text()).toContain("No upcoming capacity plans.");
});

test("planner validates dates in the real editor, previews and saves the checked payload", async () => {
  Repository.get.mockResolvedValue({ data: { plans: [] } });
  Repository.post
    .mockResolvedValueOnce({ data: { segments: [] } })
    .mockResolvedValueOnce({ data: { forecast: { segments: [] } } });
  await render(CapacityPlanner);
  await click("Plan resource usage");
  await field("Start date").get("input").setValue("2999-01-01");
  await field("End date").get("input").setValue("2998-01-01");
  await flushPromises();
  const submit = [...document.querySelectorAll("button")].find(
    (node) => node.textContent.trim() === "Check planned capacity"
  );
  expect(submit.disabled).toBe(true);
  expect(Repository.post).not.toHaveBeenCalled();
  await field("End date").get("input").setValue("2999-01-02");
  await flushPromises();
  await click("Check planned capacity");
  expect(Repository.post).toHaveBeenCalledWith(
    "/projects/11/capacity/preview",
    expect.objectContaining({
      starts_at: new Date(2999, 0, 1).toISOString(),
      ends_at: new Date(2999, 0, 2).toISOString(),
      auto_create: false,
    })
  );
  const checked = Repository.post.mock.calls[0][1];
  await click("Save plan");
  expect(Repository.post).toHaveBeenLastCalledWith("/projects/11/capacity", checked);
  expect(wrapper.text()).toContain("Capacity plan saved.");
  expect(wrapper.find('input[type="date"]').exists()).toBe(false);
});

test("a late template cannot reopen a planner form after switching projects", async () => {
  Repository.get.mockResolvedValue({ data: { plans: [] } });
  await render(CapacityPlanner);
  const pending = deferred();
  TemplateRepository.get.mockReturnValueOnce(pending.promise);
  await click("Plan resource usage");
  await select("Project").setValue(22);
  await flushPromises();
  pending.resolve({ data: specs() });
  await flushPromises();
  expect(wrapper.find('input[type="date"]').exists()).toBe(false);
});

test("editing a plan through the table preserves its definition and saves to the same ID", async () => {
  Repository.get.mockResolvedValue({ data: { plans: [plan(42, 2, { can_edit: true })] } });
  await render(CapacityPlanner);
  Repository.get.mockResolvedValueOnce({
    data: { ...plan(42, 2, { can_edit: true }), definition: specs(), auto_create: false },
  });
  await click("Edit");
  expect(Repository.get).toHaveBeenLastCalledWith("/projects/11/capacity/42");
  expect(field("Cluster name").get("input").element.value).toBe("test");
  await field("End date").get("input").setValue("2999-02-01");
  await flushPromises();
  Repository.post.mockResolvedValueOnce({ data: { segments: [] } });
  await click("Check planned capacity");
  expect(Repository.post).toHaveBeenLastCalledWith("/projects/11/capacity/42/preview", expect.any(Object));
  Repository.put.mockResolvedValueOnce({ data: { forecast: { segments: [] } } });
  await click("Save plan");
  expect(Repository.put).toHaveBeenCalledWith(
    "/projects/11/capacity/42",
    expect.objectContaining({
      definition: expect.objectContaining({ cluster_name: "test" }),
      ends_at: new Date(2999, 1, 1).toISOString(),
    })
  );
});

test("Usage shows a request error, clears report data, and can retry", async () => {
  await render(Usage);
  Repository.get.mockRejectedValueOnce({ response: { data: { message: "Report unavailable" } } });
  await click("Update");
  expect(wrapper.text()).toContain("Report unavailable");
  expect(wrapper.find("table").exists()).toBe(false);
  await click("Update");
  expect(wrapper.find("table").exists()).toBe(true);
  expect(wrapper.text()).not.toContain("Report unavailable");
});

test("unmount during access verification does not start a Usage report request", async () => {
  const pending = deferred();
  UserRepository.getCurrent.mockReturnValueOnce(pending.promise);
  await render(Usage);
  wrapper.unmount();
  pending.resolve({ data: { is_admin: true } });
  await flushPromises();
  expect(Repository.get).not.toHaveBeenCalled();
});

test("leaving the planner discards a pending report", async () => {
  const pending = deferred();
  Repository.get.mockReturnValueOnce(pending.promise);
  await render(CapacityPlanner);
  const vm = wrapper.vm;
  wrapper.unmount();
  pending.resolve({ data: { plans: [plan(42, 2)] } });
  await flushPromises();
  expect(vm.report).toEqual({});
});

test.each([false, true])(
  "create-cluster stops the card loader when resource loading settles (failure: %s)",
  async (fails) => {
    const resources = await Resources.getCloud(11);
    Resources.getCloud.mockClear();
    let resolve, reject;
    Resources.getCloud.mockReturnValueOnce(
      new Promise((done, fail) => {
        resolve = done;
        reject = fail;
      })
    );
    await render(CreateCluster);
    expect(Resources.getCloud).toHaveBeenCalledWith(11);
    const loader = wrapper.get(".v-card__loader .v-progress-linear");
    expect(loader.attributes("aria-hidden")).toBe("false");
    expect(wrapper.find('[aria-label="Loading cloud resources"]').exists()).toBe(true);
    if (fails) reject(new Error("offline"));
    else resolve(resources);
    await flushPromises();
    expect(loader.attributes("aria-hidden")).toBe("true");
    expect(wrapper.find('[aria-label="Loading cloud resources"]').exists()).toBe(false);
    if (fails) expect(wrapper.text()).toContain("Unable to load cloud resources");
  }
);
