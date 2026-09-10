import { mount, createLocalVue } from "@vue/test-utils";
import Vuetify from "vuetify";
import Vue from "vue";
import ClusterEditor from "@/components/cluster/ClusterEditor";
import Projects from "@/views/Projects";
import AvailableResourcesRepository from "@/repositories/AvailableResourcesRepository";
import UserRepository from "@/repositories/UserRepository";
import ProjectRepository from "@/repositories/ProjectRepository";

jest.mock("@/repositories/UserRepository", () => ({ getCurrent: jest.fn(), setDefaultProject: jest.fn() }));
jest.mock("@/repositories/ProjectRepository", () => ({ getAll: jest.fn() }));
jest.mock("@/repositories/AvailableResourcesRepository", () => ({
  getCloud: jest.fn(),
  getHost: jest.fn(),
  checkCloud: jest.fn(),
  checkHost: jest.fn(),
}));

Vue.use(Vuetify);
const localVue = createLocalVue();
localVue.prototype.$disableUnloadConfirmation = jest.fn();
localVue.prototype.$enableUnloadConfirmation = jest.fn();
const flush = () => new Promise(jest.requireActual("timers").setImmediate);
const projects = [
  { id: 1, name: "First project" },
  { id: 2, name: "Preferred project" },
];

function editor(existingCluster = false) {
  return mount(ClusterEditor, {
    localVue,
    vuetify: new Vuetify(),
    propsData: {
      existingCluster,
      stateful: false,
      specs: {
        cloud: { id: 1 },
        cluster_name: "existing",
        domain: "example.org",
        image: null,
        mc_version: null,
        instances: {},
        volumes: { nfs: {} },
        public_keys: [],
        guest_passwd: "password",
        nb_users: 1,
      },
    },
    stubs: ["HieradataEditor", "TypeSelect", "ResourceUsageDisplay", "router-link"],
  });
}

function projectMenu() {
  return mount(Projects, {
    localVue,
    vuetify: new Vuetify(),
    stubs: ["CloudProviderInput", "ProjectMembership"],
  });
}

beforeEach(() => {
  jest.clearAllMocks();
  UserRepository.getCurrent.mockResolvedValue({ data: { default_project_id: 2, public_keys: [] } });
  ProjectRepository.getAll.mockResolvedValue({ data: projects });
  const resources = {
    data: {
      provider: "openstack",
      possible_resources: { image: ["image"], domain: ["example.org"], mc_version: ["14.1.2"] },
      resource_details: { instance_types: [] },
    },
  };
  AvailableResourcesRepository.getCloud.mockResolvedValue(resources);
  AvailableResourcesRepository.getHost.mockResolvedValue(resources);
});

it("waits for the preference and loads only the default project, even when it is second", async () => {
  let resolveUser;
  UserRepository.getCurrent.mockReturnValue(
    new Promise((resolve) => {
      resolveUser = resolve;
    })
  );
  const wrapper = editor();
  await flush();
  expect(AvailableResourcesRepository.getCloud).not.toHaveBeenCalled();
  resolveUser({ data: { default_project_id: 2, public_keys: [] } });
  await flush();
  expect(wrapper.vm.localSpecs.cloud).toEqual({ id: 2, name: "Preferred project" });
  expect(AvailableResourcesRepository.getCloud.mock.calls).toEqual([[2]]);
  expect(AvailableResourcesRepository.checkCloud).not.toHaveBeenCalled();
  wrapper.vm.localSpecs.cloud.id = 1;
  wrapper.vm.changeCloudProject();
  await flush();
  expect(AvailableResourcesRepository.getCloud.mock.calls).toEqual([[2], [1]]);
  expect(UserRepository.setDefaultProject).not.toHaveBeenCalled();
  wrapper.destroy();
});

it("preserves the project when editing an existing cluster", async () => {
  const wrapper = editor(true);
  await flush();
  expect(wrapper.vm.localSpecs.cloud.id).toBe(1);
  expect(AvailableResourcesRepository.getHost).toHaveBeenCalledWith("existing.example.org");
  expect(AvailableResourcesRepository.getCloud).not.toHaveBeenCalled();
  wrapper.destroy();
});

it("makes no cloud requests when the user has no projects", async () => {
  UserRepository.getCurrent.mockResolvedValue({ data: { default_project_id: null, public_keys: [] } });
  ProjectRepository.getAll.mockResolvedValue({ data: [] });
  const wrapper = editor();
  await flush();
  expect(AvailableResourcesRepository.getCloud).not.toHaveBeenCalled();
  wrapper.destroy();
});

it("never shows OpenStack quotas while opening an AWS default project", async () => {
  let resolveResources;
  AvailableResourcesRepository.getCloud.mockReturnValue(
    new Promise((resolve) => {
      resolveResources = resolve;
    })
  );
  const wrapper = editor();
  const quotaIndicators = () => wrapper.findAllComponents({ name: "ResourceUsageDisplay" });
  expect(quotaIndicators().length).toBe(0);
  await flush();
  expect(wrapper.vm.loading).toBe(true);
  expect(quotaIndicators().length).toBe(0);
  resolveResources({
    data: {
      provider: "aws",
      possible_resources: { image: [], domain: ["example.org"], mc_version: [] },
      resource_details: { instance_types: [] },
    },
  });
  await flush();
  expect(wrapper.vm.isAWS).toBe(true);
  expect(quotaIndicators().length).toBe(0);
  wrapper.destroy();
});

it("hides OpenStack quotas immediately when switching projects, including failed loads", async () => {
  const quotas = Object.fromEntries(
    ["instance_count", "ram", "vcpus", "volume_count", "volume_size", "ips"].map((key) => [key, { max: 100 }])
  );
  AvailableResourcesRepository.getCloud.mockResolvedValue({
    data: {
      provider: "openstack",
      quotas,
      possible_resources: { image: [], domain: ["example.org"], mc_version: [] },
      resource_details: { instance_types: [] },
    },
  });
  const wrapper = editor();
  await flush();
  const quotaIndicators = () => wrapper.findAllComponents({ name: "ResourceUsageDisplay" });
  expect(quotaIndicators().length).toBe(6);
  let rejectResources;
  AvailableResourcesRepository.getCloud.mockReturnValue(
    new Promise((resolve, reject) => {
      rejectResources = reject;
    })
  );
  wrapper.vm.localSpecs.cloud.id = 1;
  wrapper.vm.changeCloudProject();
  await flush();
  expect(wrapper.vm.loading).toBe(true);
  expect(quotaIndicators().length).toBe(0);
  rejectResources(new Error("offline"));
  await flush();
  expect(wrapper.vm.loading).toBe(false);
  expect(quotaIndicators().length).toBe(0);
  AvailableResourcesRepository.getCloud.mockResolvedValue({
    data: {
      provider: "aws",
      possible_resources: { image: [], domain: ["example.org"], mc_version: [] },
      resource_details: { instance_types: [] },
    },
  });
  await wrapper.vm.loadCloudResources();
  await flush();
  expect(wrapper.vm.isAWS).toBe(true);
  expect(quotaIndicators().length).toBe(0);
  wrapper.destroy();
});

it.each([false, true])("clears the AWS banner while switching to OpenStack (load fails: %s)", async (fails) => {
  const resources = {
    possible_resources: { image: [], domain: ["example.org"], mc_version: [] },
    resource_details: { instance_types: [] },
  };
  AvailableResourcesRepository.getCloud.mockResolvedValue({ data: { ...resources, provider: "aws" } });
  const wrapper = editor();
  await flush();
  expect(wrapper.text()).toContain("Checking cluster feasibility");

  let resolveResources;
  let rejectResources;
  AvailableResourcesRepository.getCloud.mockReturnValue(
    new Promise((resolve, reject) => {
      resolveResources = resolve;
      rejectResources = reject;
    })
  );
  wrapper.vm.localSpecs.cloud.id = 1;
  wrapper.vm.changeCloudProject();
  await flush();
  expect(wrapper.vm.loading).toBe(true);
  expect(wrapper.vm.isAWS).toBe(false);
  expect(wrapper.findAllComponents({ name: "v-alert" }).length).toBe(0);
  expect(AvailableResourcesRepository.checkCloud).not.toHaveBeenCalled();

  if (fails) rejectResources(new Error("offline"));
  else resolveResources({ data: { ...resources, provider: "openstack" } });
  await flush();
  expect(wrapper.vm.loading).toBe(false);
  expect(wrapper.vm.isAWS).toBe(false);
  expect(wrapper.text()).not.toContain("cluster feasibility");
  expect(wrapper.text()).not.toContain("Within quotas");
  if (fails) expect(wrapper.text()).toContain("Unable to load cloud resources");
  wrapper.destroy();
});

it("lets a project member replace the default and moves the badge after saving", async () => {
  let resolveSave;
  UserRepository.setDefaultProject.mockReturnValue(
    new Promise((resolve) => {
      resolveSave = resolve;
    })
  );
  const wrapper = projectMenu();
  await flush();
  expect(wrapper.findAll("tbody tr").at(1).text()).toContain("Default");
  const button = wrapper.findAll("button").wrappers.find((button) => button.text() === "Default");
  await button.trigger("click");
  expect(UserRepository.setDefaultProject).toHaveBeenCalledWith(1);
  expect(wrapper.vm.defaultProjectId).toBe(2);
  resolveSave({ data: { default_project_id: 1 } });
  await flush();
  expect(wrapper.findAll("tbody tr").at(0).text()).toContain("Default");
  expect(wrapper.findAll("tbody tr").at(1).find("button").text()).toBe("Default");
  wrapper.destroy();
});

it("keeps the previous default and shows an error when saving fails", async () => {
  UserRepository.setDefaultProject.mockRejectedValue(new Error("offline"));
  const wrapper = projectMenu();
  await flush();
  await wrapper.vm.setDefaultProject(projects[0]);
  expect(wrapper.vm.defaultProjectId).toBe(2);
  expect(wrapper.text()).toContain("Unable to save your default project");
  expect(wrapper.vm.savingDefault).toBeNull();
  wrapper.destroy();
});
