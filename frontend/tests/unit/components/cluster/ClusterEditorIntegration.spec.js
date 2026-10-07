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

test.each([false, true])("a fully populated editor starts valid (existing cluster: %s)", async (existingCluster) => {
  await render({ existingCluster, stateful: false, preserveSpecs: true, status: "created" });
  const apply = wrapper.findAllComponents({ name: "VBtn" }).find((button) => button.text() === "Apply");
  expect(wrapper.vm.validForm).toBe(true);
  expect(wrapper.text()).not.toContain("Some form fields are invalid.");
  expect(apply.props("disabled")).toBe(false);
  await apply.trigger("click");
  await flushPromises();
  expect(wrapper.emitted("apply")).toHaveLength(1);
});

test("pending resource validation keeps Apply disabled without claiming fields are invalid", async () => {
  let resolve;
  Resources.getCloud.mockReturnValueOnce(
    new Promise((done) => {
      resolve = done;
    })
  );
  await render({ existingCluster: false, stateful: false, preserveSpecs: true });
  const apply = wrapper.findAllComponents({ name: "VBtn" }).find((button) => button.text() === "Apply");
  expect(wrapper.vm.validForm).toBeNull();
  expect(wrapper.text()).not.toContain("Some form fields are invalid.");
  expect(apply.props("disabled")).toBe(true);
  resolve({ data: resources });
  await flushPromises();
  expect(wrapper.vm.validForm).toBe(true);
  expect(apply.props("disabled")).toBe(false);
});

test("missing SSH keys disable Apply on load and correcting them clears the error", async () => {
  const configuration = specs();
  configuration.public_keys = [];
  await render({ specs: configuration, existingCluster: false, stateful: false, preserveSpecs: true });
  const apply = wrapper.findAllComponents({ name: "VBtn" }).find((button) => button.text() === "Apply");
  expect(wrapper.vm.validForm).toBe(false);
  expect(wrapper.text()).toContain("Some form fields are invalid.");
  expect(apply.props("disabled")).toBe(true);
  const keys = wrapper
    .findAllComponents({ name: "VCombobox" })
    .find((component) => component.props("label") === "SSH Keys");
  await keys.setValue(specs().public_keys);
  await flushPromises();
  expect(wrapper.vm.validForm).toBe(true);
  expect(wrapper.text()).not.toContain("Some form fields are invalid.");
  expect(apply.props("disabled")).toBe(false);
  await keys.setValue([]);
  await flushPromises();
  expect(wrapper.vm.validForm).toBe(false);
  expect(wrapper.text()).toContain("Some form fields are invalid.");
  expect(apply.props("disabled")).toBe(true);
});

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

test.each(["change", "keydown.enter"])("volume tags keep their input while typing and commit on %s", async (event) => {
  await render({ stateful: false, preserveSpecs: true });
  const tagField = () => wrapper.findAllComponents({ name: "VCombobox" }).find((field) => field.props("label") === "tag");
  const input = tagField().get("input");
  for (const value of ["n", "no", "nod", "node"]) {
    input.element.value = value;
    await input.trigger("input");
    await flushPromises();
    expect(tagField().get("input").element).toBe(input.element);
    expect(input.element.value).toBe(value);
    expect(wrapper.vm.specs.volumes.nfs.home.size).toBe(50);
    expect(wrapper.vm.specs.volumes.node).toBeUndefined();
  }
  await input.trigger(event);
  await flushPromises();
  expect(wrapper.vm.specs.volumes.node.home.size).toBe(50);
  expect(wrapper.vm.specs.volumes.nfs.home).toBeUndefined();
});

test("selecting an existing volume tag commits the selected group", async () => {
  const configuration = specs();
  configuration.volumes.node = { scratch: { size: 100 } };
  await render({ specs: configuration, stateful: false, preserveSpecs: true });
  const tag = wrapper.findAllComponents({ name: "VCombobox" }).find((field) => field.props("label") === "tag");
  await tag.get(".v-field").trigger("mousedown");
  await flushPromises();
  const option = [...document.querySelectorAll('[role="option"]')].find((item) => item.textContent === "node");
  expect(option).toBeDefined();
  option.click();
  await flushPromises();
  expect(wrapper.vm.specs.volumes.node).toEqual({ home: { size: 50 }, scratch: { size: 100 } });
  expect(wrapper.vm.specs.volumes.nfs.home).toBeUndefined();
});

test("correcting instance counts clears quota errors on unchanged type fields and enables Apply", async () => {
  await render({ stateful: false, preserveSpecs: true });
  await field("count").get("input").setValue("10001");
  await wrapper.vm.apply();
  await flushPromises();
  const apply = () => wrapper.findAllComponents({ name: "VBtn" }).find((button) => button.text() === "Apply");
  expect(apply().props("disabled")).toBe(true);
  expect(wrapper.text()).toContain("Ram quota exceeded");
  expect(wrapper.emitted("apply")).toBeUndefined();

  await field("count").get("input").setValue("2");
  await flushPromises();
  expect(wrapper.text()).not.toContain("Ram quota exceeded");
  expect(wrapper.text()).not.toContain("Core quota exceeded");
  expect(apply().props("disabled")).toBe(false);
  await apply().trigger("click");
  await flushPromises();
  expect(wrapper.emitted("apply")).toHaveLength(1);
});

test.each([false, true])("AWS rechecks clear stale type errors while preserving other errors (%s)", async (invalidPassword) => {
  const configuration = specs();
  configuration.instances.node.count = 3;
  Resources.getHost.mockResolvedValue({ data: { ...resources, provider: "aws" } });
  Resources.checkHost.mockResolvedValueOnce({
    data: { feasibility: { status: "blocked", issues: [] }, instance_choices: { node: [] } },
  });
  await render({ specs: configuration, stateful: false, preserveSpecs: true });
  await wrapper.vm.checkAWS();
  const type = wrapper.findComponent({ name: "TypeSelect" }).findComponent({ name: "VSelect" });
  await type.vm.validate();
  if (invalidPassword) await field("Guest password").get("input").setValue("short");
  await flushPromises();
  expect(wrapper.text()).toContain("This type is unavailable");
  const apply = () => wrapper.findAllComponents({ name: "VBtn" }).find((button) => button.text() === "Apply");
  expect(apply().props("disabled")).toBe(true);

  Resources.checkHost.mockResolvedValueOnce({
    data: { feasibility: { status: "ready", issues: [] }, instance_choices: { node: ["p1"] } },
  });
  await field("count").get("input").setValue("2");
  await wrapper.vm.checkAWS();
  await flushPromises();
  expect(wrapper.vm.awsStatus).toBe("ready");
  expect(configuration.instances.node.type).toBe("p1");
  expect(wrapper.text()).not.toContain("This type is unavailable");
  expect(apply().props("disabled")).toBe(invalidPassword);
  if (invalidPassword) {
    expect(wrapper.text()).toContain("The password must be at least");
    await field("Guest password").get("input").setValue("password");
    await flushPromises();
  }
  expect(apply().props("disabled")).toBe(false);
  await apply().trigger("click");
  await flushPromises();
  expect(wrapper.emitted("apply")).toHaveLength(1);
});

test("removing an oversized volume clears quota errors on the remaining volume", async () => {
  const configuration = specs();
  configuration.instances.node.tags.push("nfs");
  configuration.volumes.nfs.extra = { size: 10001 };
  await render({ specs: configuration, stateful: false, preserveSpecs: true });
  await wrapper.vm.apply();
  await flushPromises();
  expect(wrapper.text()).toContain("Volume size quota exceeded");

  wrapper.vm.rmVolumeRow("extra");
  await flushPromises();
  expect(wrapper.text()).not.toContain("Volume size quota exceeded");
  expect(wrapper.vm.applyButtonEnabled).toBe(true);
});

test("volume totals include every matching instance group, fractional sizes, and boot volumes", async () => {
  const configuration = specs();
  configuration.instances = {
    mgmt: { count: 1, type: "p1", tags: ["nfs"] },
    node: { count: 3, type: "p1", tags: ["node"] },
    worker: { count: 2, type: "p1", tags: ["node"] },
    disabled: { count: 0, type: "p1", tags: ["node", "unused"] },
  };
  configuration.volumes.node = { scratch: { size: 20.5 } };
  configuration.volumes.unused = { data: { size: 1000 } };
  configuration.volumes.unmatched = { data: { size: 1000 } };
  Resources.getHost.mockResolvedValue({
    data: {
      ...resources,
      resource_details: {
        instance_types: [{ name: "p1", ram: 1024, vcpus: 1, required_volume_count: 1, required_volume_size: 10 }],
      },
    },
  });
  await render({ specs: configuration });
  expect(wrapper.vm.volumeCountUsed).toBe(12);
  expect(wrapper.vm.volumeSizeUsed).toBe(212.5);
  const displays = wrapper.findAllComponents({ name: "ResourceUsageDisplay" });
  expect(displays.find((display) => display.props("title") === "volumes").props("used")).toBe(12);
  expect(displays.find((display) => display.props("title") === "volume storage").props("used")).toBe(212.5);
});

test.each([
  ["volume_count", 2, "Volume number quota exceeded"],
  ["volume_size", 120, "Volume size quota exceeded"],
])("retagging preserves %s validation and correcting instance counts clears the error", async (quota, max, error) => {
  const configuration = specs();
  configuration.instances.mgmt = { count: 1, type: "p1", tags: ["nfs"] };
  configuration.instances.node.count = 3;
  Resources.getHost.mockResolvedValue({ data: { ...resources, quotas: { ...resources.quotas, [quota]: { max } } } });
  await render({ specs: configuration, stateful: false, preserveSpecs: true });
  expect(wrapper.vm.volumeCountUsed).toBe(1);
  expect(wrapper.vm.volumeSizeUsed).toBe(50);
  const tag = wrapper.findAllComponents({ name: "VCombobox" }).find((field) => field.props("label") === "tag");
  await tag.get("input").setValue("node");
  await flushPromises();
  expect(wrapper.vm.volumeCountUsed).toBe(3);
  expect(wrapper.vm.volumeSizeUsed).toBe(150);
  await wrapper.vm.apply();
  await flushPromises();
  expect(wrapper.text()).toContain(error);
  expect(wrapper.emitted("apply")).toBeUndefined();

  await field("count").get("input").setValue("1");
  await flushPromises();
  expect(wrapper.vm.volumeCountUsed).toBe(1);
  expect(wrapper.vm.volumeSizeUsed).toBe(50);
  expect(wrapper.text()).not.toContain(error);
  expect(wrapper.vm.applyButtonEnabled).toBe(true);
  await wrapper.vm.apply();
  expect(wrapper.emitted("apply")).toHaveLength(1);
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
