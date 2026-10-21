import { flushPromises } from "@vue/test-utils";
import { shallowMountWithVuetify as mount, cleanupMounts } from "../../../helpers/mount";
import AgentAvailability from "@/components/cluster/AgentAvailability";
import Projects from "@/repositories/ProjectRepository";

jest.mock("@/repositories/ProjectRepository", () => ({ agentAvailability: jest.fn() }));

beforeEach(() => {
  jest.useFakeTimers();
  jest.clearAllMocks();
});
afterEach(() => {
  cleanupMounts();
  jest.useRealTimers();
});
const render = () => mount(AgentAvailability, {
  props: { projectId: 1 }, global: { renderStubDefaultSlot: true },
});

test("blocks while loading, warns on outage, and automatically enables after recovery", async () => {
  let respond;
  Projects.agentAvailability.mockImplementationOnce(() => new Promise((resolve) => { respond = resolve; }));
  const wrapper = render();
  expect(wrapper.emitted("availability").at(-1)).toEqual([false]);
  expect(wrapper.text()).toContain("Checking");
  respond({ data: { available: false, message: "Agent offline" } });
  await flushPromises();
  expect(wrapper.text()).toContain("Agent offline");
  expect(wrapper.emitted("availability").at(-1)).toEqual([false]);
  Projects.agentAvailability.mockResolvedValue({ data: { available: true } });
  jest.advanceTimersByTime(30000);
  await flushPromises();
  expect(wrapper.emitted("availability").at(-1)).toEqual([true]);
  expect(wrapper.text()).toBe("");
  expect(Projects.agentAvailability).toHaveBeenCalledTimes(2);
  jest.advanceTimersByTime(299999);
  await flushPromises();
  expect(Projects.agentAvailability).toHaveBeenCalledTimes(2);
  Projects.agentAvailability.mockRejectedValueOnce(new Error("network"));
  jest.advanceTimersByTime(1);
  await flushPromises();
  expect(Projects.agentAvailability).toHaveBeenCalledTimes(3);
  expect(wrapper.emitted("availability").at(-1)).toEqual([false]);
  jest.advanceTimersByTime(30000);
  await flushPromises();
  expect(Projects.agentAvailability).toHaveBeenCalledTimes(4);
  expect(wrapper.emitted("availability").at(-1)).toEqual([true]);
  wrapper.unmount();
  expect(jest.getTimerCount()).toBe(0);
});

test("blocks when the check fails and ignores stale responses after switching projects", async () => {
  let respond;
  Projects.agentAvailability.mockImplementationOnce(() => new Promise((resolve) => { respond = resolve; }));
  const wrapper = render();
  Projects.agentAvailability.mockRejectedValue(new Error("network"));
  await wrapper.setProps({ projectId: 2 });
  await flushPromises();
  expect(wrapper.text()).toContain("Could not verify");
  respond({ data: { available: true } });
  await flushPromises();
  expect(wrapper.emitted("availability").at(-1)).toEqual([false]);
  expect(wrapper.text()).toContain("Could not verify");
});

test("does not update or schedule another check after unmounting", async () => {
  let respond;
  Projects.agentAvailability.mockImplementationOnce(() => new Promise((resolve) => { respond = resolve; }));
  const onAvailability = jest.fn();
  const wrapper = mount(AgentAvailability, { props: { projectId: 1, onAvailability } });
  onAvailability.mockClear();
  wrapper.unmount();
  respond({ data: { available: true } });
  await flushPromises();
  expect(onAvailability).not.toHaveBeenCalled();
  expect(jest.getTimerCount()).toBe(0);
});
