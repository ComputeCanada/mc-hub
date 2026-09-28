import { mount, flushPromises } from "@vue/test-utils";
import { createAppVuetify } from "@/plugins/vuetify";
import ClusterEditor from "@/components/cluster/ClusterEditor";
import Resources from "@/repositories/AvailableResourcesRepository";
import Users from "@/repositories/UserRepository";
import Projects from "@/repositories/ProjectRepository";

jest.mock("@/repositories/AvailableResourcesRepository", () => ({
  getHost: jest.fn(),
  getCloud: jest.fn(),
  checkHost: jest.fn(),
  checkCloud: jest.fn(),
}));
jest.mock("@/repositories/UserRepository", () => ({ getCurrent: jest.fn() }));
jest.mock("@/repositories/ProjectRepository", () => ({ getAll: jest.fn() }));
const resources = {
  provider: "openstack",
  possible_resources: { domain: ["example.org"], mc_version: ["14"], image: ["image"], types: ["p1"], tag_types: {} },
  resource_details: {
    instance_types: [{ name: "p1", ram: 1024, vcpus: 1, required_volume_count: 0, required_volume_size: 0 }],
  },
  quotas: Object.fromEntries(
    ["instance_count", "ram", "vcpus", "volume_count", "volume_size", "ips"].map((key) => [key, { max: 10000 }])
  ),
};
const specs = () => ({
  cloud: { id: 1, name: "First" },
  cluster_name: "test",
  domain: "example.org",
  mc_version: "14",
  image: "image",
  instances: { node: { count: 1, type: "p1", tags: ["node"] } },
  volumes: { nfs: { home: { size: 50 } } },
  public_keys: ["ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAITest comment"],
  guest_passwd: "password",
  nb_users: 1,
});
let wrapper, warn, mocks;
beforeEach(() => {
  jest.clearAllMocks();
  Resources.getHost.mockResolvedValue({ data: resources });
  Resources.getCloud.mockResolvedValue({ data: resources });
  Users.getCurrent.mockResolvedValue({ data: { public_keys: [], default_project_id: 1 } });
  Projects.getAll.mockResolvedValue({
    data: [
      { id: 1, name: "First" },
      { id: 2, name: "Second" },
    ],
  });
  mocks = { $enableUnloadConfirmation: jest.fn(), $disableUnloadConfirmation: jest.fn() };
  warn = jest.spyOn(console, "warn");
});
afterEach(() => {
  if (wrapper?.exists()) wrapper.unmount();
  expect(warn).not.toHaveBeenCalled();
  jest.restoreAllMocks();
});
async function render(props = {}) {
  wrapper = mount(ClusterEditor, {
    props: { specs: specs(), existingCluster: true, stateful: true, ...props },
    global: { plugins: [createAppVuetify()], mocks, stubs: { RouterLink: { template: "<a><slot/></a>" } } },
  });
  await flushPromises();
  return wrapper;
}
function field(label) {
  return wrapper.findAllComponents({ name: "VTextField" }).find((component) => component.props("label") === label);
}

test("real controls rename rows, edit volumes and emit apply only after validation", async () => {
  await render({ stateful: false, preserveSpecs: true });
  await field("hostname prefix").get("input").setValue("worker");
  expect(wrapper.vm.specs.instances.worker.type).toBe("p1");
  expect(wrapper.vm.specs.instances.node).toBeUndefined();
  await field("volume name").get("input").setValue("data");
  expect(wrapper.vm.specs.volumes.nfs.data.size).toBe(50);
  await field("size").get("input").setValue("0");
  await wrapper.vm.apply();
  expect(wrapper.emitted("apply")).toBeUndefined();
  await field("size").get("input").setValue("100");
  await Promise.all([wrapper.vm.apply(), wrapper.vm.apply()]);
  expect(wrapper.vm.specs.volumes.nfs.data.size).toBe(100);
  expect(wrapper.emitted("apply")).toHaveLength(1);
});

test("date picker preserves local calendar dates and supports clearing", async () => {
  await render();
  const date = new Date(2030, 0, 2);
  wrapper.vm.expirationDate = date;
  await flushPromises();
  expect(wrapper.vm.specs.expiration_date).toBe("2030-01-02");
  expect(wrapper.vm.expirationDate.getDate()).toBe(2);
  expect(field("Expiration date").props("modelValue")).toBe("2030-01-02");
  await field("Expiration date").setValue(null);
  expect(wrapper.vm.expirationDate).toBeNull();
  expect(wrapper.vm.expirationRule("2000-01-01")).not.toBe(true);
});

test("project selection refreshes resources and ignores an older request", async () => {
  await render({ existingCluster: false, stateful: false, preserveSpecs: true });
  let resolve;
  Resources.getCloud.mockReturnValueOnce(
    new Promise((done) => {
      resolve = done;
    })
  );
  const pending = wrapper.vm.loadCloudResources();
  const selector = wrapper
    .findAllComponents({ name: "VSelect" })
    .find((component) => component.props("label") === "Cloud project");
  await selector.setValue(2);
  await flushPromises();
  expect(Resources.getCloud).toHaveBeenLastCalledWith(2);
  expect(wrapper.vm.specs.cloud).toEqual({ id: 2, name: "Second" });
  resolve({ data: { ...resources, provider: "aws" } });
  await pending;
  expect(wrapper.vm.provider).toBe("openstack");
});

test("unmount clears unload protection and discards pending resource responses", async () => {
  await render();
  await field("count").get("input").setValue("2");
  expect(mocks.$enableUnloadConfirmation).toHaveBeenCalled();
  let resolve;
  Resources.getHost.mockReturnValueOnce(
    new Promise((done) => {
      resolve = done;
    })
  );
  const vm = wrapper.vm;
  const request = vm.loadCloudResources();
  wrapper.unmount();
  resolve({ data: resources });
  await request;
  expect(vm.provider).toBeNull();
  expect(mocks.$disableUnloadConfirmation).toHaveBeenCalled();
});

test("removing an invalid settings row clears its blocking error", async () => {
  await render();
  await field("Root disk size").get("input").setValue("-1");
  expect(wrapper.vm.instanceSettingsErrors.node).toBe(true);
  wrapper.vm.rmInstanceRow("node");
  await flushPromises();
  expect(wrapper.vm.instanceSettingsErrors).toEqual({});
});
