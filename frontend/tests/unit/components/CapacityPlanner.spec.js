import Vue from "vue";
import Vuetify from "vuetify";
import { shallowMount } from "@vue/test-utils";
import CapacityPlanner from "@/views/CapacityPlanner";
import ClusterEditor from "@/components/cluster/ClusterEditor";
import Repository from "@/repositories/Repository";
import ProjectRepository from "@/repositories/ProjectRepository";
import TemplateRepository from "@/repositories/TemplateRepository";

Vue.use(Vuetify);
jest.mock("@/repositories/Repository", () => ({ get: jest.fn(), post: jest.fn(), delete: jest.fn() }));
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
  await wrapper.vm.preview();
  expect(wrapper.vm.hasShortages(wrapper.vm.previewReport)).toBe(true);
  await wrapper.vm.save();
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

test("creation links include both the project and plan", async () => {
  await flush();
  expect(wrapper.vm.creationLink({ id: 42 })).toEqual({
    path: "/create-cluster",
    query: { capacityProject: 1, capacityPlan: 42 },
  });
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

test.each([
  [{ name: "g2-24gb-32" }, 6],
  [{ name: "gpu12-120-850gb-a100x1" }, 3],
  [{ name: "p4d.24xlarge", gpus: [{ count: 8 }] }, 24],
  [{ name: "g6f.large", gpus: [{ count: 1, partition_size: 0.125 }] }, 0.375],
])("the form counts GPU allocations across instance groups: %s", (type, expected) => {
  const count = ClusterEditor.computed.gpuUsed.call({
    usedResourcesLoaded: true,
    resourceDetails: { instance_types: [type, { name: "cpu" }] },
    instances: [
      { type: type.name, count: 3 },
      { type: "cpu", count: 5 },
    ],
  });
  expect(count).toBe(expected);
});
