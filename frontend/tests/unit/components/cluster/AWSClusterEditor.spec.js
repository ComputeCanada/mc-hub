import { mount, shallowMount, createLocalVue } from "@vue/test-utils";
import Vuetify from "vuetify";
import Vue from "vue";
import ClusterEditor from "@/components/cluster/ClusterEditor";
import AvailableResourcesRepository from "@/repositories/AvailableResourcesRepository";
import UserRepository from "@/repositories/UserRepository";
import ProjectRepository from "@/repositories/ProjectRepository";

jest.mock("@/repositories/UserRepository", () => ({ getCurrent: jest.fn() }));
jest.mock("@/repositories/ProjectRepository", () => ({ getAll: jest.fn() }));

jest.mock("@/repositories/AvailableResourcesRepository", () => ({
  getCloud: jest.fn(),
  getHost: jest.fn(),
  checkCloud: jest.fn(),
  checkHost: jest.fn(),
}));

Vue.use(Vuetify);
const localVue = createLocalVue();
localVue.use(Vuetify);
localVue.prototype.$disableUnloadConfirmation = jest.fn();
localVue.prototype.$enableUnloadConfirmation = jest.fn();

function editor() {
  return shallowMount(
    { ...ClusterEditor, created() {}, updated() {} },
    {
      localVue,
      vuetify: new Vuetify(),
      propsData: {
        existingCluster: false,
        specs: {
          cloud: { id: 1 },
          instances: { node: { count: 4, type: "m6i.xlarge", tags: ["node"] } },
          volumes: {},
          image: "ami-test",
          availability_zone: null,
          mc_version: "14.1.2",
          guest_passwd: "password",
          public_keys: [],
          cluster_name: "test",
          domain: "example.org",
        },
      },
      data: () => ({
        provider: "aws",
        validForm: true,
        possibleResources: { types: [], image: ["ami-test"], domain: ["example.org"], mc_version: ["14.1.2"] },
        resourceDetails: { instance_types: [{ name: "m6i.large" }, { name: "m6i.xlarge" }] },
      }),
    }
  );
}

describe("AWS cluster feasibility", () => {
  beforeEach(() => {
    jest.useFakeTimers();
    jest.clearAllMocks();
  });
  afterEach(() => {
    jest.useRealTimers();
  });

  it("shows the saved availability zone when reopening an undeployed cluster", async () => {
    const seed = editor();
    const specs = { ...seed.vm.localSpecs, undeployed: true, availability_zone: "ca-central-1b" };
    seed.destroy();
    UserRepository.getCurrent.mockResolvedValue({ data: { public_keys: [] } });
    ProjectRepository.getAll.mockResolvedValue({ data: [{ id: 1, name: "AWS" }] });
    AvailableResourcesRepository.getHost.mockResolvedValue({
      data: {
        provider: "aws",
        possible_resources: {
          image: ["ami-test"],
          domain: ["example.org"],
          mc_version: ["14.1.2"],
          availability_zone: ["ca-central-1a", "ca-central-1b"],
        },
        resource_details: { instance_types: [] },
      },
    });
    const wrapper = mount(ClusterEditor, {
      localVue,
      vuetify: new Vuetify(),
      propsData: { specs, existingCluster: true, stateful: false, status: "not_deployed" },
      stubs: ["HieradataEditor", "TypeSelect", "ResourceUsageDisplay", "router-link"],
    });
    await new Promise(jest.requireActual("timers").setImmediate);
    await wrapper.vm.$nextTick();
    expect(wrapper.text()).toContain("ca-central-1b");
    expect(wrapper.vm.localSpecs.availability_zone).toBe("ca-central-1b");
    wrapper.destroy();
  });

  it("preserves home, project and scratch and supports adding AWS volume rows", async () => {
    const wrapper = editor();
    const nfs = { home: { size: 100 }, project: { size: 100 }, scratch: { size: 100 } };
    await wrapper.setData({ localSpecs: { ...wrapper.vm.localSpecs, volumes: { nfs } } });
    AvailableResourcesRepository.getCloud.mockResolvedValue({
      data: {
        provider: "aws",
        resource_details: wrapper.vm.resourceDetails,
        possible_resources: wrapper.vm.possibleResources,
      },
    });
    await wrapper.vm.loadCloudResources();
    expect(wrapper.vm.localSpecs.volumes.nfs).toEqual(nfs);
    expect(wrapper.text()).toContain("Add volume row");
    expect(
      wrapper.findAll("v-text-field-stub").wrappers.filter((w) => w.attributes("label") === "volume name").length
    ).toBe(3);
    wrapper.vm.addVolumeRow();
    expect(wrapper.vm.localSpecs.volumes.nfs.volume1).toEqual({ size: 50 });
    expect(wrapper.vm.awsDefinition.volumes.nfs.volume1).toEqual({ size: 50 });
    expect(wrapper.vm.awsVolumeSizeRule(1.5)).not.toBe(true);
    wrapper.vm.rmVolumeRow("volume1");
    expect(wrapper.vm.localSpecs.volumes.nfs.volume1).toBeUndefined();
    wrapper.destroy();
  });

  it("shows loading and accepts all checked defaults without another round trip", async () => {
    const wrapper = editor();
    wrapper.vm.localSpecs.instances.node.type = null;
    await wrapper.vm.$nextTick();
    expect(wrapper.findComponent({ name: "TypeSelect" }).props("loading")).toBe(true);
    AvailableResourcesRepository.checkCloud.mockResolvedValue({
      data: {
        feasibility: { status: "ready", issues: [] },
        instance_choices: { node: ["m6i.large"] },
        instance_defaults: { node: "m6i.large" },
      },
    });
    await wrapper.vm.checkAWS();
    await wrapper.vm.$nextTick();
    expect(wrapper.vm.localSpecs.instances.node.type).toBe("m6i.large");
    expect(wrapper.vm.awsStatus).toBe("ready");
    expect(wrapper.findComponent({ name: "TypeSelect" }).props("loading")).toBe(false);
    jest.advanceTimersByTime(1000);
    expect(AvailableResourcesRepository.checkCloud).toHaveBeenCalledTimes(1);
    wrapper.destroy();
  });

  it("waits for an in-flight check before submitting the latest edits", async () => {
    let resolve;
    AvailableResourcesRepository.checkCloud.mockReturnValueOnce(
      new Promise((r) => {
        resolve = r;
      })
    );
    const wrapper = editor();
    const first = wrapper.vm.checkAWS();
    wrapper.vm.localSpecs.instances.node.count = 2;
    await wrapper.vm.$nextTick();
    jest.advanceTimersByTime(500);
    expect(AvailableResourcesRepository.checkCloud).toHaveBeenCalledTimes(1);
    AvailableResourcesRepository.checkCloud.mockResolvedValueOnce({
      data: {
        feasibility: { status: "ready", issues: [] },
        instance_choices: { node: ["m6i.xlarge"] },
      },
    });
    resolve({ data: { feasibility: { status: "ready", issues: [] }, instance_choices: {} } });
    await first;
    expect(wrapper.vm.awsFeasibility).toBeNull();
    jest.advanceTimersByTime(500);
    expect(AvailableResourcesRepository.checkCloud).toHaveBeenCalledTimes(2);
    expect(AvailableResourcesRepository.checkCloud.mock.calls[1][1].instances.node.count).toBe(2);
    wrapper.destroy();
  });

  it("invalidates a pending response when edits revert to a previously checked definition", async () => {
    const wrapper = editor();
    await wrapper.setData({
      awsCheckedDefinition: JSON.stringify(wrapper.vm.awsDefinition),
      awsFeasibility: { status: "ready", issues: [] },
    });
    wrapper.vm.localSpecs.instances.node.count = 2;
    await wrapper.vm.$nextTick();
    let resolve;
    AvailableResourcesRepository.checkCloud.mockReturnValueOnce(
      new Promise((r) => {
        resolve = r;
      })
    );
    const request = wrapper.vm.checkAWS();
    wrapper.vm.localSpecs.instances.node.count = 4;
    await wrapper.vm.$nextTick();
    resolve({ data: { feasibility: { status: "ready", issues: [] }, instance_choices: {} } });
    await request;
    expect(wrapper.vm.awsFeasibility).toBeNull();
    wrapper.destroy();
  });

  it("filters options by group while preserving an invalid selection", async () => {
    const wrapper = editor();
    await wrapper.setData({
      awsChoices: { node: ["m6i.large"] },
      awsFeasibility: { status: "blocked", issues: [{ message: "Insufficient Standard vCPUs" }] },
    });
    expect(wrapper.vm.getTypes(["node"], "node")).toEqual([
      { name: "m6i.large", unavailable: false },
      { name: "m6i.xlarge", unavailable: true },
    ]);
    expect(wrapper.vm.localSpecs.instances.node.type).toBe("m6i.xlarge");
    expect(wrapper.vm.applyButtonEnabled).toBe(false);
    expect(wrapper.text()).toContain("Insufficient Standard vCPUs");
    expect(wrapper.findComponent({ name: "ResourceUsageDisplay" }).exists()).toBe(false);
    wrapper.destroy();
  });

  it("keeps every type selector usable while a changed type is checked in the background", async () => {
    const wrapper = editor();
    wrapper.vm.$set(wrapper.vm.localSpecs.instances, "login", { count: 1, type: "m6i.large", tags: ["login"] });
    await wrapper.vm.$nextTick();
    const choices = { node: ["m6i.large", "m6i.xlarge"], login: ["m6i.large", "m6i.xlarge"] };
    await wrapper.setData({
      awsChoices: choices,
      awsChoicesLoaded: true,
      awsChecking: false,
      awsFeasibility: { status: "ready", issues: [] },
    });
    const selectors = wrapper.findAllComponents({ name: "TypeSelect" });
    selectors.at(0).vm.$emit("input", "m6i.large");
    await wrapper.vm.$nextTick();
    expect(wrapper.vm.awsChecking).toBe(true);
    expect(wrapper.vm.awsChoices).toEqual(choices);
    selectors.wrappers.forEach((selector) => {
      expect(selector.props("loading")).toBe(false);
      expect(selector.props("types")).toHaveLength(2);
    });
    expect(wrapper.vm.applyButtonEnabled).toBe(false);

    AvailableResourcesRepository.checkCloud.mockResolvedValueOnce({
      data: {
        feasibility: { status: "ready", issues: [] },
        instance_choices: { node: ["m6i.large", "m6i.xlarge"], login: ["m6i.large"] },
      },
    });
    await wrapper.vm.checkAWS();
    expect(wrapper.vm.awsChoices.login).toEqual(["m6i.large"]);
    expect(wrapper.vm.localSpecs.instances.node.type).toBe("m6i.large");
    expect(wrapper.vm.localSpecs.instances.login.type).toBe("m6i.large");
    wrapper.destroy();
  });

  it("retains loaded type choices when a background feasibility check fails", async () => {
    const wrapper = editor();
    await wrapper.setData({ awsChoices: { node: ["m6i.large", "m6i.xlarge"] }, awsChoicesLoaded: true });
    AvailableResourcesRepository.checkCloud.mockRejectedValueOnce(new Error("offline"));
    await wrapper.vm.checkAWS();
    expect(wrapper.findComponent({ name: "TypeSelect" }).props("loading")).toBe(false);
    expect(wrapper.vm.getTypes(["node"], "node")).toHaveLength(2);
    expect(wrapper.vm.awsError).toContain("Retry");
    expect(wrapper.vm.applyButtonEnabled).toBe(false);
    wrapper.destroy();
  });

  it("invalidates green status immediately and ignores a stale response", async () => {
    let resolve;
    AvailableResourcesRepository.checkCloud.mockReturnValue(
      new Promise((r) => {
        resolve = r;
      })
    );
    const wrapper = editor();
    await wrapper.setData({ awsFeasibility: { status: "ready", issues: [] } });
    const check = wrapper.vm.checkAWS();
    wrapper.vm.localSpecs.instances.node.count = 20;
    await wrapper.vm.$nextTick();
    expect(wrapper.vm.applyButtonEnabled).toBe(false);
    resolve({ data: { feasibility: { status: "ready", issues: [] }, instance_choices: { node: ["m6i.xlarge"] } } });
    await check;
    expect(wrapper.vm.awsFeasibility).toBeNull();
    expect(wrapper.vm.awsChoices).toEqual({});
    wrapper.destroy();
  });

  it("keeps verification failures distinct from quota blockers and supports retry", async () => {
    AvailableResourcesRepository.checkCloud.mockRejectedValueOnce(new Error("offline"));
    const wrapper = editor();
    await wrapper.vm.checkAWS();
    expect(wrapper.vm.awsFeasibility).toBeNull();
    expect(wrapper.vm.awsError).toContain("Retry");
    expect(wrapper.vm.applyButtonEnabled).toBe(false);
    AvailableResourcesRepository.checkCloud.mockResolvedValueOnce({
      data: { feasibility: { status: "ready", issues: [] }, instance_choices: { node: ["m6i.xlarge"] } },
    });
    await wrapper.vm.checkAWS();
    expect(wrapper.vm.awsStatus).toBe("ready");
    wrapper.destroy();
  });

  it("selects and clears an optional zone, marks edits dirty, and rechecks feasibility", async () => {
    const wrapper = editor();
    await wrapper.setProps({ existingCluster: true });
    await wrapper.setData({
      initialSpecs: JSON.parse(JSON.stringify(wrapper.vm.localSpecs)),
      possibleResources: { ...wrapper.vm.possibleResources, availability_zone: ["ca-central-1a", "ca-central-1b"] },
      awsFeasibility: { status: "ready", issues: [] },
    });
    expect(wrapper.vm.dirtyForm).toBe(false);
    const selector = wrapper
      .findAllComponents({ name: "v-select" })
      .wrappers.find((select) => select.props("label") === "Availability zone (optional)");
    expect(selector.props("items")).toEqual(["ca-central-1a", "ca-central-1b"]);
    expect(selector.props("clearable")).toBe(true);
    selector.vm.$emit("input", "ca-central-1a");
    await wrapper.vm.$nextTick();
    expect(wrapper.vm.localSpecs.availability_zone).toBe("ca-central-1a");
    expect(wrapper.vm.dirtyForm).toBe(true);
    expect(wrapper.vm.awsFeasibility).toBeNull();
    AvailableResourcesRepository.checkHost.mockResolvedValue({
      data: { feasibility: { status: "ready", issues: [] }, instance_choices: { node: ["m6i.xlarge"] } },
    });
    await wrapper.vm.checkAWS();
    expect(AvailableResourcesRepository.checkHost.mock.calls[0][1].availability_zone).toBe("ca-central-1a");
    selector.vm.$emit("input", null);
    await wrapper.vm.$nextTick();
    expect(wrapper.vm.awsDefinition.availability_zone).toBeNull();
    expect(wrapper.vm.awsFeasibility).toBeNull();
    wrapper.destroy();
  });
});
