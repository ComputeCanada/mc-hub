import { mount, flushPromises } from "@vue/test-utils";
import { createRouter, createMemoryHistory } from "vue-router";
import { createAppVuetify } from "@/plugins/vuetify";
import ClustersList from "@/components/cluster/ClustersList";
import Repository from "@/repositories/MagicCastleRepository";

jest.mock("@/repositories/MagicCastleRepository", () => ({ getAll: jest.fn() }));
const clusters = ["alpha", "beta"].map((name) => ({
  hostname: `${name}.example.org`,
  cluster_name: name,
  domain: "example.org",
  cloud: { name: "Research" },
  owner: "alice@example.org",
  status: "provisioning_success",
  services: {},
  nb_users: 10,
  guest_passwd: "secret",
}));
let wrapper, host, warn;
beforeEach(() => {
  jest.useFakeTimers();
  Repository.getAll.mockReset().mockResolvedValue({ data: clusters });
  host = document.createElement("div");
  document.body.append(host);
  warn = jest.spyOn(console, "warn");
});
afterEach(() => {
  if (wrapper?.exists()) wrapper.unmount();
  host.remove();
  expect(warn).not.toHaveBeenCalled();
  jest.useRealTimers();
  jest.restoreAllMocks();
});
async function render() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: ["/", "/create-cluster", "/clusters/:hostname"].map((path) => ({
      path,
      component: { template: "<div />" },
    })),
  });
  await router.push("/");
  await router.isReady();
  wrapper = mount(ClustersList, { attachTo: host, global: { plugins: [createAppVuetify(), router] } });
  await flushPromises();
  return router;
}
function rows() {
  return wrapper.findAll("tbody > tr.v-data-table__tr");
}

test("expands one hostname, retains it across refresh, and navigates the teardown action", async () => {
  const router = await render();
  expect(wrapper.text()).toContain("Research");
  await rows()[0].trigger("click");
  expect(wrapper.vm.expandedRows).toEqual(["alpha.example.org"]);
  expect(wrapper.findAll("tr.cluster-overview")).toHaveLength(1);
  Repository.getAll.mockResolvedValue({ data: structuredClone(clusters) });
  await wrapper.vm.loadMagicCastlesStatus();
  expect(wrapper.vm.expandedRows).toEqual(["alpha.example.org"]);
  await rows()[1].trigger("click");
  expect(wrapper.vm.expandedRows).toEqual(["beta.example.org"]);
  expect(wrapper.findAll("tr.cluster-overview")).toHaveLength(1);
  await wrapper
    .findAll("button")
    .find((button) => button.text().includes("Tear down"))
    .trigger("click");
  await flushPromises();
  jest.advanceTimersByTime(1);
  await flushPromises();
  expect(router.currentRoute.value.path).toBe("/clusters/beta.example.org");
  expect(router.currentRoute.value.query).toEqual({ destroy: "1" });
  expect(wrapper.vm.expandedRows).toEqual(["beta.example.org"]);
});

test("the expand button preserves single expansion and removed clusters close their overview", async () => {
  await render();
  await rows()[0].get("button").trigger("click");
  await rows()[1].get("button").trigger("click");
  expect(wrapper.vm.expandedRows).toEqual(["beta.example.org"]);
  Repository.getAll.mockResolvedValue({ data: [clusters[0]] });
  await wrapper.vm.loadMagicCastlesStatus();
  expect(wrapper.vm.expandedRows).toEqual([]);
});

test("errors preserve previous rows and polling retries without overlapping requests", async () => {
  await render();
  let reject;
  Repository.getAll.mockReturnValueOnce(
    new Promise((resolve, fail) => {
      reject = fail;
    })
  );
  const request = wrapper.vm.loadMagicCastlesStatus();
  jest.advanceTimersByTime(10000);
  expect(Repository.getAll).toHaveBeenCalledTimes(2);
  reject(new Error("offline"));
  await request;
  expect(wrapper.vm.magicCastles).toEqual(clusters);
  expect(wrapper.text()).toContain("Unable to load clusters");
  jest.advanceTimersByTime(5000);
  await flushPromises();
  expect(wrapper.vm.error).toBe("");
});

test("unmount stops polling and discards a pending refresh", async () => {
  await render();
  let resolve;
  Repository.getAll.mockReturnValueOnce(
    new Promise((done) => {
      resolve = done;
    })
  );
  const vm = wrapper.vm,
    request = vm.loadMagicCastlesStatus();
  wrapper.unmount();
  resolve({ data: [] });
  await request;
  jest.advanceTimersByTime(10000);
  expect(vm.magicCastles).toEqual(clusters);
  expect(Repository.getAll).toHaveBeenCalledTimes(2);
  expect(jest.getTimerCount()).toBe(0);
});

describe("ClustersList service health", () => {
  const jupyterhub = {
    label: "JupyterHub",
    url: "https://jupyter.example.com",
    status: "healthy",
  };
  const freeipa = {
    label: "FreeIPA",
    url: "https://ipa.example.com",
    status: "unavailable",
  };

  const methods = ClustersList.methods;

  it("uses green for an available service", () => {
    expect(methods.serviceStatusColor(jupyterhub)).toBe("green");
    expect(methods.serviceStatusLabel(jupyterhub)).toBe("JupyterHub is available");
  });

  it("uses red for an unhealthy service", () => {
    expect(methods.serviceStatusColor(freeipa)).toBe("red");
    expect(methods.serviceStatusLabel(freeipa)).toBe("FreeIPA is unhealthy");
  });
});
