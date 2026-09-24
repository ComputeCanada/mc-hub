import Vue from "vue";
import Vuetify from "vuetify";
import { VDataTable } from "vuetify/lib";
import { mount, shallowMount } from "@vue/test-utils";
import CapacityPlanner from "@/views/CapacityPlanner";
import ClusterEditor from "@/components/cluster/ClusterEditor";
import Repository from "@/repositories/Repository";
import ProjectRepository from "@/repositories/ProjectRepository";
import TemplateRepository from "@/repositories/TemplateRepository";

Vue.use(Vuetify);
jest.mock("@/repositories/Repository", () => ({ get: jest.fn(), post: jest.fn(), put: jest.fn(), delete: jest.fn() }));
jest.mock("@/repositories/ProjectRepository", () => ({ getAll: jest.fn() }));
jest.mock("@/repositories/TemplateRepository", () => ({ get: jest.fn() }));
const flush = () => new Promise(jest.requireActual("timers").setImmediate);
let wrapper;
beforeEach(() => {
  jest.clearAllMocks();
  ProjectRepository.getAll.mockResolvedValue({ data: [{ id: 1, name: "Project" }] });
  Repository.get.mockResolvedValue({ data: { plans: [], forecast: null } });
  TemplateRepository.get.mockResolvedValue({ data: { cloud: { id: 1 }, cluster_name: "example" } });
  wrapper = shallowMount(CapacityPlanner, { mocks: { $route: { query: {} } } });
});
afterEach(() => wrapper.destroy());

async function fillForm() {
  await flush();
  await wrapper.vm.newPlan();
  await wrapper.setData({ startsAt: "2999-01-01", endsAt: "2999-01-02" });
}

test("reuses the cluster editor in planning mode and saves despite quota warnings", async () => {
  await fillForm();
  expect(wrapper.findComponent(ClusterEditor).props("plannerMode")).toBe(true);
  const forecast = {
    segments: [{ starts_at: "2999-01-01T12:00:00Z", ends_at: "2999-01-02T12:00:00Z", shortages: { vcpus: 4 } }],
  };
  Repository.post.mockResolvedValueOnce({ data: forecast }).mockResolvedValueOnce({ data: { forecast } });
  const editor = wrapper.findComponent(ClusterEditor);
  expect(editor.props("submitLabel")).toBe("Check planned capacity");
  editor.vm.$emit("apply");
  await flush();
  expect(wrapper.vm.hasShortages(wrapper.vm.previewReport)).toBe(true);
  expect(editor.props("submitLabel")).toBe("Save plan");
  editor.vm.$emit("apply");
  await flush();
  expect(Repository.post.mock.calls[1][0]).toBe("/projects/1/capacity");
  expect(Repository.post.mock.calls[1][1].auto_create).toBe(false);
  expect(Repository.post.mock.calls[1][1].starts_at).toBe(new Date(2999, 0, 1).toISOString());
  expect(Repository.post.mock.calls[1][1].ends_at).toBe(new Date(2999, 0, 2).toISOString());
  expect(wrapper.vm.notice).toContain("saved with quota conflicts");
});

test("editing dates invalidates the checked forecast", async () => {
  await fillForm();
  Repository.post.mockResolvedValue({ data: { segments: [] } });
  await wrapper.vm.preview();
  expect(wrapper.vm.checkedPayload).not.toBeNull();
  await wrapper.setData({ endsAt: "2999-01-03" });
  expect(wrapper.vm.checkedPayload).toBeNull();
  expect(wrapper.vm.previewReport).toBeNull();
  expect(wrapper.findComponent(ClusterEditor).props("submitLabel")).toBe("Check planned capacity");
});

test("late preview responses cannot validate a changed form", async () => {
  await fillForm();
  let resolve;
  Repository.post.mockReturnValue(
    new Promise((r) => {
      resolve = r;
    })
  );
  const request = wrapper.vm.preview();
  await wrapper.setData({ autoCreate: true });
  resolve({ data: { segments: [] } });
  await request;
  expect(wrapper.vm.checkedPayload).toBeNull();
});

test("edit loads saved configuration and updates the same plan", async () => {
  await flush();
  const definition = { cloud: { id: 1 }, cluster_name: "saved-name", guest_passwd: "saved-password" };
  Repository.get.mockResolvedValueOnce({
    data: {
      id: 42,
      can_edit: true,
      definition,
      auto_create: true,
      starts_at: new Date(2999, 0, 1).toISOString(),
      ends_at: new Date(2999, 0, 2).toISOString(),
    },
  });
  await wrapper.vm.editPlan({ id: 42 });
  expect(wrapper.vm.startsAt).toBe("2999-01-01");
  expect(wrapper.vm.autoCreate).toBe(true);
  expect(wrapper.vm.specs).toEqual(definition);
  expect(wrapper.findComponent(ClusterEditor).props("preserveSpecs")).toBe(true);
  Repository.post.mockResolvedValueOnce({ data: { segments: [] } });
  Repository.put.mockResolvedValueOnce({ data: { forecast: { segments: [] } } });
  await wrapper.vm.preview();
  expect(Repository.post).toHaveBeenCalledWith("/projects/1/capacity/42/preview", expect.any(Object));
  await wrapper.vm.save();
  expect(Repository.put).toHaveBeenCalledWith("/projects/1/capacity/42", expect.objectContaining({ definition }));
  expect(Repository.post).not.toHaveBeenCalledWith("/projects/1/capacity", expect.anything());
});

test("planning does not let current quota block submission", () => {
  expect(ClusterEditor.computed.coreRule.call({ plannerMode: true, vcpuUsed: 10, vcpuMax: 1 })).toBe(true);
  expect(ClusterEditor.computed.coreRule.call({ plannerMode: false, vcpuUsed: 10, vcpuMax: 1 })).toBe(
    "Core quota exceeded"
  );
});

test("a prefilled manual cluster can be submitted without changing its resources", () => {
  const enabled = ClusterEditor.computed.applyButtonEnabled.call({
    loading: false,
    validForm: true,
    plannerMode: false,
    benchmarkMode: false,
    existingCluster: false,
    preserveSpecs: true,
    dirtyForm: false,
    resourceError: "",
    isAWS: false,
  });
  expect(enabled).toBe(true);
});

test("upcoming resource columns sort numeric totals, including GPUs and AWS pools", async () => {
  await flush();
  await wrapper.setData({
    report: {
      plans: [
        { id: 1, name: "Ten GPUs", demand: { gpus: 10, vcpus: 2, "Standard (A, C, D, H, I, M, R, T, Z)": 20 } },
        { id: 2, name: "Two GPUs", demand: { gpus: 2, vcpus: 10, "Standard (A, C, D, H, I, M, R, T, Z)": 4 } },
      ],
    },
  });
  const column = (key) => wrapper.vm.resourceColumns.find((c) => c.key === key);
  expect(wrapper.vm.headers.some((h) => h.value === "demand")).toBe(false);
  const table = mount(VDataTable, {
    vuetify: new Vuetify(),
    propsData: {
      headers: wrapper.vm.headers,
      items: wrapper.vm.planRows,
      sortBy: column("gpus").value,
      itemsPerPage: -1,
    },
  });
  try {
    const names = () => table.findAll("tbody tr").wrappers.map((row) => row.find("td").text());
    expect(names()).toEqual(["Two GPUs", "Ten GPUs"]);
    await table.setProps({ sortBy: column("vcpus").value });
    expect(names()).toEqual(["Ten GPUs", "Two GPUs"]);
    await table.setProps({ sortBy: column("Standard (A, C, D, H, I, M, R, T, Z)").value });
    expect(names()).toEqual(["Two GPUs", "Ten GPUs"]);
    await table.setProps({ sortDesc: true });
    expect(names()).toEqual(["Ten GPUs", "Two GPUs"]);
  } finally {
    table.destroy();
  }
});

test("future demand columns sort GPU and RAM totals numerically, including empty intervals", async () => {
  await flush();
  const segment = (day, demand) => ({
    starts_at: `2999-01-${day}T00:00:00Z`,
    ends_at: `2999-02-01T00:00:00Z`,
    demand,
    shortages: {},
  });
  await wrapper.setData({
    report: {
      forecast: {
        segments: [segment("01", { gpus: 10, ram: 2048 }), segment("02", { gpus: 2, ram: 10240 }), segment("03", {})],
      },
    },
  });
  const column = (key) => wrapper.vm.resourceColumns.find((c) => c.key === key);
  expect(column("ram").text).toBe("RAM (GiB)");
  expect(wrapper.vm.forecastRows.map((row) => row[column("ram").value])).toEqual([2, 10, 0]);
  expect(wrapper.vm.resources({ ram: 1536 })).toBe("RAM (GiB): 1.5");
  const table = mount(VDataTable, {
    vuetify: new Vuetify(),
    propsData: {
      headers: wrapper.vm.forecastHeaders,
      items: wrapper.vm.forecastRows,
      itemKey: "starts_at",
      sortBy: column("gpus").value,
      itemsPerPage: -1,
    },
  });
  try {
    const days = () => table.findAll("tbody tr").wrappers.map((row) => row.find("td").text().slice(8, 10));
    expect(days()).toEqual(["03", "02", "01"]);
    await table.setProps({ sortBy: column("ram").value });
    expect(days()).toEqual(["03", "01", "02"]);
    await table.setProps({ sortDesc: true });
    expect(days()).toEqual(["02", "01", "03"]);
    await table.setProps({ sortBy: "starts_at", sortDesc: false });
    expect(days()).toEqual(["01", "02", "03"]);
  } finally {
    table.destroy();
  }
});

test("cancelling the editor discards the form without changing the saved plan", async () => {
  await fillForm();
  await wrapper.setData({ editingId: 42, autoCreate: true });
  await wrapper.setData({ previewReport: { segments: [] }, checkedPayload: { definition: wrapper.vm.specs } });
  wrapper.findComponent(ClusterEditor).vm.$emit("cancel");
  await wrapper.vm.$nextTick();
  expect(wrapper.findComponent(ClusterEditor).exists()).toBe(false);
  expect(wrapper.vm.editingId).toBeNull();
  expect(wrapper.vm.checkedPayload).toBeNull();
  expect(wrapper.vm.previewReport).toBeNull();
  expect(wrapper.vm.startsAt).toBe("");
  expect(wrapper.vm.endsAt).toBe("");
  expect(wrapper.vm.autoCreate).toBe(false);
  expect(Repository.put).not.toHaveBeenCalled();
  expect(Repository.post).not.toHaveBeenCalled();
  expect(Repository.delete).not.toHaveBeenCalled();
});

test.each(["resources", "automatic creation"])("changing %s resets the Save plan button", async (field) => {
  await fillForm();
  Repository.post.mockResolvedValue({ data: { segments: [] } });
  await wrapper.vm.preview();
  await wrapper.vm.$nextTick();
  expect(wrapper.findComponent(ClusterEditor).props("submitLabel")).toBe("Save plan");
  if (field === "resources") {
    await wrapper.setData({ specs: { ...wrapper.vm.specs, instances: { node: { count: 2, type: "g1-8gb" } } } });
  } else {
    await wrapper.setData({ autoCreate: true });
  }
  expect(wrapper.findComponent(ClusterEditor).props("submitLabel")).toBe("Check planned capacity");
  expect(wrapper.vm.checkedPayload).toBeNull();
});

test("planner displays the day-before shortage in GiB and explains when external alerts are disabled", async () => {
  await flush();
  await wrapper.setData({
    report: {
      plans: [],
      preflight: {
        status: "insufficient",
        checked_at: "2999-01-01T00:00:00Z",
        notifications_enabled: false,
        checks: [{ starts_at: "2999-01-02T00:00:00Z", shortages: { ram: 2048, vcpus: 4 } }],
      },
    },
  });
  expect(wrapper.text()).toContain("24-hour quota check");
  expect(wrapper.text()).toContain("RAM (GiB): 2");
  expect(wrapper.text()).toContain("External notifications are not configured");
});
