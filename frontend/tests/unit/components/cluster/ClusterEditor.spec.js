import ClusterEditor from "@/components/cluster/ClusterEditor";
import { mount, createLocalVue } from "@vue/test-utils";
import UnloadConfirmation from "@/plugins/UnloadConfirmation";
import Vuetify from "vuetify";
import Vue from "vue";
import router from "@/router";
import { cloneDeep } from "lodash";
import moxios from 'moxios';
import Repository from "@/repositories/Repository";

Vue.use(Vuetify);

const localVue = createLocalVue();
const vuetify = new Vuetify();
localVue.use(Vuetify);
localVue.use(UnloadConfirmation, { router });

const DEFAULT_USER = Object.freeze({
  public_keys: [],
});

const DEFAULT_MAGIC_CASTLE = Object.freeze({
  cloud: {"id" : 1, "name": "arbutus"},
  cluster_name: "",
  domain: "magic-castle.cloud",
  image: "Rocky-8.7-x64-2023-02",
  mc_version: "14.1.2",
  nb_users: 10,
  instances: {
    mgmt: {
      type: "p4-6gb",
      count: 1,
      tags: ["mgmt", "puppet", "nfs"]
    },
    login: {
      type: "p2-3gb",
      count: 1,
      tags: ["login", "public", "proxy"]
    },
    node: {
      type: "p1-1.5gb",
      count: 5,
      tags: ["node"]
    }
  },
  volumes: {
    nfs: {
      home: { size: 100 },
      project: { size: 50 },
      scratch: { size: 20.6 },
    }
  },
  public_keys: [],
  guest_passwd: ""
});

const DEFAULT_POSSIBLE_RESOURCES = Object.freeze({
  image: ["centos7", "centos7-updated", "Rocky-8.7-x64-2023-02", "CentOS-8-x64-2019-11", "CentOS-7-x64-2019-01"],
  mc_version: ["14.1.2", "14.0.0"],
  tag_types: {"mgmt": ["p4-6gb", "c2-7.5gb-31"], "login": ["p2-3gb", "p4-6gb"], "node": ["p2-3gb", "p4-6gb"]},
  "types": ["p1-1.5gb", "p2-3gb", "p4-6gb"],
  volumes: {},
  domain: ["magic-castle.cloud", "mc.ca"]
});

const DEFAULT_QUOTAS = Object.freeze({
  instance_count: { max: 115 },
  ram: { max: 221184 },
  vcpus: { max: 224 },
  volume_count: { max: 114 },
  volume_size: { max: 490 },
  ips: { max: 3 },
});

const DEFAULT_RESOURCE_DETAILS = Object.freeze({
  instance_types: [
    { name: "p1-1.5gb", vcpus: 1, ram: 1536, required_volume_count: 1, required_volume_size: 8 },
    { name: "p2-3gb", vcpus: 2, ram: 3072, required_volume_count: 1, required_volume_size: 10 },
    { name: "p4-6gb", vcpus: 4, ram: 6144, required_volume_count: 0, required_volume_size: 0 },
    { name: "c64-256gb-10", vcpus: 64, ram: 253952, required_volume_count: 0, required_volume_size: 0 }
  ]
});


async function getDefaultClusterEditorWrapper(existingCluster=true, hostname="test1.magic-castle.cloud") {
  let wrapper = mount(ClusterEditor, {
    localVue,
    router,
    vuetify,
    propsData: {
      specs: cloneDeep(DEFAULT_MAGIC_CASTLE),
      existingCluster: existingCluster,
      hostname: hostname,
      stateful: true,
    }
  });
  await wrapper.vm.promise;
  return wrapper;
}

describe("ClusterEditor", () => {

  beforeEach(function () {
    // import and pass your custom axios instance to this method
    moxios.install(Repository)
    moxios.wait(function () {
      let request = moxios.requests.mostRecent();
      if(request.url.includes("/available-resources")) {
        request.respondWith({
          status: 200,
          response: {
            'possible_resources': DEFAULT_POSSIBLE_RESOURCES,
            'quotas': DEFAULT_QUOTAS,
            'resource_details': DEFAULT_RESOURCE_DETAILS
          }
        })
      } else if (request.url.includes("/users/me")) {
        request.respondWith({
          status: 200,
          response: DEFAULT_USER
        })
      } else {
        console.log(request.url);
      }
    })
  })

  afterEach(function () {
    // import and pass your custom axios instance to this method
    moxios.uninstall(Repository)
  })

  it("expands one instance at a time and retains optional settings when collapsed", async () => {
    const wrapper = await getDefaultClusterEditorWrapper();
    const mgmt = wrapper.find('[aria-controls="instance-settings-mgmt"]');
    const login = wrapper.find('[aria-controls="instance-settings-login"]');
    expect(mgmt.attributes("aria-expanded")).toBe("false");
    await mgmt.trigger("click");
    expect(mgmt.attributes("aria-expanded")).toBe("true");
    const settings = wrapper.findAllComponents({ name: "InstanceSettings" }).wrappers
      .find(component => component.props("name") === "mgmt");
    const disk = settings.findAllComponents({ name: "v-text-field" }).wrappers
      .find(component => component.props("label") === "Root disk size");
    disk.vm.$emit("input", "100");
    await login.trigger("click");
    expect(mgmt.attributes("aria-expanded")).toBe("false");
    expect(login.attributes("aria-expanded")).toBe("true");
    expect(wrapper.vm.specs.instances.mgmt.disk_size).toBe(100);
    expect(wrapper.text()).toContain("1 set");
    await login.trigger("click");
    expect(login.attributes("aria-expanded")).toBe("false");
    wrapper.destroy();
  });

  it("detects GPU types using cloud metadata or the OpenStack flavor name", () => {
    const resourceDetails = { instance_types: [
      { name: "g1-10gb-4" },
      { name: "gpu12-120-850gb-a100x1", gpus: [] },
      { name: "p4-6gb" },
      { name: "p4d.24xlarge", gpus: [{ count: 8 }] },
      { name: "g6f.large", gpus: [{ count: null, partition_size: 0.125 }] },
      { name: "g1-8gb-4", gpus: [] },
      { name: "g2-16gb-8", gpus: 0 },
      { name: "p8-16gb", gpus: [] },
    ] };
    for (const name of ["g1-10gb-4", "p4d.24xlarge", "g6f.large", "g1-8gb-4", "g2-16gb-8", "g1-32gb-8", "gpu12-120-850gb-a100x1"]) {
      expect(ClusterEditor.methods.instanceHasGpu.call({ resourceDetails }, name)).toBe(true);
    }
    for (const name of ["p4-6gb", "p8-16gb", "unknown", null]) {
      expect(ClusterEditor.methods.instanceHasGpu.call({ resourceDetails }, name)).toBe(false);
    }
  });

  it("magicCastleGuestPasswordNonExisting", async () => {
    const clusterEditorWrapperNew = await getDefaultClusterEditorWrapper(false);
    expect(clusterEditorWrapperNew.vm.specs.guest_passwd.length).toBe(12);
  });

  it("magicCastleGuestPasswordExisting", async () => {
    const clusterEditorWrapperExisting = await getDefaultClusterEditorWrapper(true);
    expect(clusterEditorWrapperExisting.vm.specs.guest_passwd.length).toBe(0);
  });

  it("defaults to the first vetted Magic Castle version", async () => {
    const specs = cloneDeep(DEFAULT_MAGIC_CASTLE);
    specs.mc_version = null;
    const wrapper = mount(ClusterEditor, {
      localVue,
      router,
      vuetify,
      propsData: {
        specs,
        existingCluster: false,
        stateful: true,
      }
    });

    await wrapper.vm.promise;
    await wrapper.vm.$nextTick();

    expect(wrapper.vm.specs.mc_version).toBe(DEFAULT_POSSIBLE_RESOURCES.mc_version[0]);
  });

  it("allows changing the version of an undeployed cluster", async () => {
    const wrapper = await getDefaultClusterEditorWrapper();
    await wrapper.setProps({
      specs: { ...cloneDeep(DEFAULT_MAGIC_CASTLE), undeployed: true },
      stateful: false,
    });

    const versionSelect = wrapper.findAllComponents({ name: "v-select" })
      .wrappers.find((select) => select.props("label") === "Magic Castle Version");
    expect(versionSelect).toBeDefined();
    versionSelect.vm.$emit("input", "14.0.0");
    await wrapper.vm.$nextTick();

    expect(wrapper.vm.specs.mc_version).toBe("14.0.0");
    expect(wrapper.vm.dirtyForm).toBe(true);
  });

  it("keeps the version read-only for a deployed cluster", async () => {
    const wrapper = await getDefaultClusterEditorWrapper();

    const versionSelect = wrapper.findAllComponents({ name: "v-select" })
      .wrappers.find((select) => select.props("label") === "Magic Castle Version");
    expect(versionSelect).toBeUndefined();
    expect(wrapper.text()).toContain(DEFAULT_MAGIC_CASTLE.mc_version);
  });

  it("ramGbUsed", async () => {
    const clusterEditorWrapper = await getDefaultClusterEditorWrapper();

    // used = 6 + 3 + 1.5 * 5 GB = 16.5 GB
    expect(clusterEditorWrapper.vm.ramGbUsed).toBe(16.5);
  });

  it("ramGbMax", async () => {
    const clusterEditorWrapper = await getDefaultClusterEditorWrapper();

    // available = 221184 MB = 216 GB
    expect(clusterEditorWrapper.vm.ramGbMax).toBe(216);
  });

  it("vcpuUsed", async () => {
    const clusterEditorWrapper = await getDefaultClusterEditorWrapper();

    // used = 4 + 2 + 1 * 5
    expect(clusterEditorWrapper.vm.vcpuUsed).toBe(11);
  });

  it("vcpuMax", async () => {
    const clusterEditorWrapper = await getDefaultClusterEditorWrapper();

    // available = 224
    expect(clusterEditorWrapper.vm.vcpuMax).toBe(224);
  });

  it("volumeCountUsed", async () => {
    const clusterEditorWrapper = await getDefaultClusterEditorWrapper();

    // used = 3 (storage volumes) + 1 (login) + 5 (node)
    expect(clusterEditorWrapper.vm.volumeCountUsed).toBe(9);
  });

  it("volumeCountMax", async () => {
    const clusterEditorWrapper = await getDefaultClusterEditorWrapper();

    // available = 114
    expect(clusterEditorWrapper.vm.volumeCountMax).toBe(114);
  });

  it("volumeSizeUsed", async () => {
    const clusterEditorWrapper = await getDefaultClusterEditorWrapper();

    // used = 100 + 50 + 20.6 (storage volumes) + 10 (login) + 5 * 8 (node)
    expect(clusterEditorWrapper.vm.volumeSizeUsed).toBe(220.6);
  });

  it("volumeSizeMax", async () => {
    const clusterEditorWrapper = await getDefaultClusterEditorWrapper();
    expect(clusterEditorWrapper.vm.volumeSizeMax).toBe(490);
  });
});
