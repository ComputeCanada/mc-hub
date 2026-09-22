import { shallowMount } from "@vue/test-utils";
import axios from "axios";
import Vue from "vue";
import ServiceStatusBanner from "@/components/ui/ServiceStatusBanner";

jest.mock("axios", () => ({ get: jest.fn() }));
const flush = async () => {
  await Promise.resolve();
  await Promise.resolve();
  await Vue.nextTick();
};
const provider = (overrides = {}) => ({
  provider: "terraform_cloud",
  name: "Terraform Cloud",
  freshness: "fresh",
  last_success_at: new Date().toISOString(),
  reported_status: "no_incidents",
  affected_components: [],
  incidents: [],
  status_url: "https://status.hashicorp.com/",
  ...overrides,
});
const mount = () => shallowMount(ServiceStatusBanner, { stubs: ["v-alert", "v-btn"] });

beforeEach(() => {
  jest.useFakeTimers();
  Object.defineProperty(document, "hidden", { configurable: true, value: false });
  axios.get.mockReset();
});
afterEach(() => jest.useRealTimers());

it("hides healthy status, shows multiple providers and clears on recovery", async () => {
  axios.get.mockResolvedValue({ data: { providers: [provider()] } });
  const wrapper = mount();
  await flush();
  expect(wrapper.vm.visible).toBe(false);
  axios.get.mockResolvedValue({
    data: {
      providers: [
        provider({ reported_status: "disruption" }),
        provider({ provider: "github", name: "GitHub", reported_status: "disruption" }),
      ],
    },
  });
  await wrapper.vm.refresh();
  expect(wrapper.text()).toContain("Terraform Cloud and GitHub report service disruptions");
  axios.get.mockResolvedValue({ data: { providers: [provider()] } });
  await wrapper.vm.refresh();
  expect(wrapper.vm.visible).toBe(false);
  wrapper.destroy();
});

it("preserves warnings on fetch failure and renders incident content as text", async () => {
  axios.get.mockResolvedValue({
    data: {
      providers: [
        provider({
          reported_status: "disruption",
          incidents: [
            {
              id: "one",
              title: "<script>incident</script>",
              confirmed: false,
              status: "investigating",
              url: "https://status.hashicorp.com/",
            },
          ],
        }),
      ],
    },
  });
  const wrapper = mount();
  await flush();
  await wrapper.setData({ expanded: true });
  expect(wrapper.find("script").exists()).toBe(false);
  expect(wrapper.text()).toContain("current status unconfirmed");
  axios.get.mockRejectedValue(new Error("offline"));
  await wrapper.vm.refresh();
  expect(wrapper.text()).toContain("last reported a service disruption");
  expect(wrapper.text()).toContain("Status updates unavailable");
  wrapper.destroy();
});

it("handles stale and initial unknown status, pauses hidden polling and cleans up", async () => {
  axios.get.mockResolvedValue({ data: { providers: [provider({ freshness: "unknown", last_success_at: null })] } });
  const wrapper = mount();
  await flush();
  expect(wrapper.text()).toContain("Service status unavailable");
  Object.defineProperty(document, "hidden", { configurable: true, value: true });
  jest.advanceTimersByTime(60000);
  expect(axios.get).toHaveBeenCalledTimes(1);
  Object.defineProperty(document, "hidden", { configurable: true, value: false });
  axios.get.mockResolvedValue({
    data: { providers: [provider({ last_success_at: new Date(Date.now() - 240000).toISOString() })] },
  });
  document.dispatchEvent(new Event("visibilitychange"));
  await flush();
  expect(wrapper.vm.unavailable).toBe(true);
  wrapper.destroy();
  jest.advanceTimersByTime(60000);
  expect(axios.get).toHaveBeenCalledTimes(2);
});
