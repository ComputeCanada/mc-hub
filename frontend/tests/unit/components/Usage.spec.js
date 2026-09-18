import Vue from "vue";
import Vuetify from "vuetify";
import { shallowMount } from "@vue/test-utils";
import Usage from "@/views/Usage";
import Repository from "@/repositories/Repository";
import UserRepository from "@/repositories/UserRepository";

Vue.use(Vuetify);
jest.mock("@/repositories/Repository", () => ({ get: jest.fn() }));
jest.mock("@/repositories/UserRepository", () => ({ getCurrent: jest.fn() }));
const flush = () => new Promise(jest.requireActual("timers").setImmediate);
const emptyDurations = { count: 0, average_seconds: null, median_seconds: null, p95_seconds: null };
const report = {
  projects: [],
  summary: {},
  months: [],
  attempts: [],
  attempt_count: 0,
  apply_to_healthy: emptyDurations,
  completed_lifetime: emptyDurations,
  ongoing_age: emptyDurations,
  last_poll_at: null,
};

beforeEach(() => {
  jest.clearAllMocks();
  UserRepository.getCurrent.mockResolvedValue({ data: { is_admin: true } });
  Repository.get.mockResolvedValue({ data: report });
});

test("non-admin direct visits cannot request or render report data", async () => {
  UserRepository.getCurrent.mockResolvedValue({ data: { is_admin: false } });
  const wrapper = shallowMount(Usage);
  await flush();
  expect(Repository.get).not.toHaveBeenCalled();
  expect(wrapper.text()).toContain("Only hub admins");
  expect(wrapper.find("v-data-table-stub").exists()).toBe(false);
  wrapper.destroy();
});

test("admin report handles empty measurements, stale observations and filters", async () => {
  const wrapper = shallowMount(Usage);
  await flush();
  expect(wrapper.vm.duration(null)).toBe("—");
  expect(wrapper.text()).toContain("Background observations are overdue");
  await wrapper.setData({ start: "2026-01-01", end: "2026-02-28", project: "project-uuid" });
  await wrapper.vm.load(2);
  expect(Repository.get).toHaveBeenLastCalledWith("/usage", {
    params: { start: "2026-01-01", end: "2026-02-28", project: "project-uuid", page: 2 },
  });
  Repository.get.mockRejectedValue({ response: { status: 403, data: { message: "Only hub admins" } } });
  await wrapper.vm.load();
  expect(wrapper.vm.report).toBeNull();
  expect(wrapper.text()).toContain("Only hub admins");
  wrapper.destroy();
});
