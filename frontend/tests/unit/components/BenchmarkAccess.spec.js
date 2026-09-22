import Vue from "vue";
import Vuetify from "vuetify";
import { shallowMount } from "@vue/test-utils";
import App from "@/App";
import ProjectRepository from "@/repositories/ProjectRepository";
import { benchmarkAccess, refreshBenchmarkAccess, guardBenchmarkAccess } from "@/services/benchmarkAccess";

Vue.use(Vuetify);
jest.mock("@/repositories/ProjectRepository", () => ({ getAll: jest.fn() }));
const flush = () => new Promise(jest.requireActual("timers").setImmediate);
const route = { matched: [{ meta: { requiresProjectAdmin: true } }] };

beforeEach(() => {
  jest.clearAllMocks();
  benchmarkAccess.allowed = false;
});

test.each([[], [{ admin: false }], [{ admin: false }, { admin: false }]].map((projects) => [projects]))(
  "users without an administered project cannot navigate to benchmarks or see its button: %j",
  async (projects) => {
    ProjectRepository.getAll.mockResolvedValue({ data: projects });
    const wrapper = shallowMount(App, { mocks: { $route: {} }, stubs: ["router-view"] });
    await flush();
    expect(wrapper.find('[to="/benchmarks"]').exists()).toBe(false);
    const next = jest.fn();
    await guardBenchmarkAccess(route, {}, next);
    expect(next).toHaveBeenCalledWith({ path: "/", replace: true });
    wrapper.destroy();
  }
);

test("one administered project enables navigation and the top-bar button", async () => {
  ProjectRepository.getAll.mockResolvedValue({ data: [{ admin: false }, { admin: true }] });
  const wrapper = shallowMount(App, { mocks: { $route: {} }, stubs: ["router-view"] });
  await flush();
  expect(wrapper.find('[to="/benchmarks"]').exists()).toBe(true);
  const next = jest.fn();
  await guardBenchmarkAccess(route, {}, next);
  expect(next).toHaveBeenCalledWith();
  ProjectRepository.getAll.mockResolvedValue({ data: [{ admin: false }] });
  await refreshBenchmarkAccess();
  await wrapper.vm.$nextTick();
  expect(wrapper.find('[to="/benchmarks"]').exists()).toBe(false);
  wrapper.destroy();
});

test("permission lookup failures deny access and clear previously granted navigation", async () => {
  benchmarkAccess.allowed = true;
  ProjectRepository.getAll.mockRejectedValue(new Error("Unavailable"));
  const next = jest.fn();
  await guardBenchmarkAccess(route, {}, next);
  expect(benchmarkAccess.allowed).toBe(false);
  expect(next).toHaveBeenCalledWith({ path: "/", replace: true });
});

test("ordinary routes do not require a project administrator role", async () => {
  const next = jest.fn();
  await guardBenchmarkAccess({ matched: [{ meta: {} }] }, {}, next);
  expect(next).toHaveBeenCalledWith();
  expect(ProjectRepository.getAll).not.toHaveBeenCalled();
});
