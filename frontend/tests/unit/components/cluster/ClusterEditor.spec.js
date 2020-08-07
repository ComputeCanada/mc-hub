import ClusterEditor from "@/components/cluster/ClusterEditor";
import { mount, createLocalVue } from "@vue/test-utils";
import UnloadConfirmation from "@/plugins/UnloadConfirmation";
import Vuetify from "vuetify";
import Vue from "vue";
import router from "@/router";
import { cloneDeep } from "lodash";

Vue.use(Vuetify);

const localVue = createLocalVue();
const vuetify = new Vuetify();
localVue.use(Vuetify);
localVue.use(UnloadConfirmation, { router });

const DEFAULT_MAGIC_CASTLE = Object.freeze({
  cluster_name: "phoenix",
  domain: "calculquebec.cloud",
  image: "CentOS-7-x64-2019-07",
  nb_users: 10,
  instances: {
    mgmt: {
      type: "p4-6gb",
      count: 1
    },
    login: {
      type: "p2-3gb",
      count: 1
    },
    node: {
      type: "p1-1.5gb",
      count: 5
    }
  },
  storage: {
    type: "nfs",
    home_size: 100,
    project_size: 50,
    scratch_size: 20.6
  },
  public_keys: [""],
  guest_passwd: "",
  os_floating_ips: []
});

const DEFAULT_POSSIBLE_RESOURCES = Object.freeze({
  image: ["centos7", "centos7-updated", "CentOS-7-x64-2019-07", "CentOS-8-x64-2019-11", "CentOS-7-x64-2019-01"],
  instances: {
    mgmt: { type: ["p4-6gb", "c64-256gb-10"] },
    login: { type: ["p2-3gb", "p4-6gb", "c64-256gb-10"] },
    node: { type: ["p2-3gb", "p4-6gb", "c64-256gb-10"] }
  },
  os_floating_ips: ["206.12.94.21"],
  storage: { type: ["nfs"] },
  domain: ["calculquebec.cloud", "c3.ca"]
});

const DEFAULT_QUOTAS = Object.freeze({
  instance_count: { max: 115 },
  ram: { max: 221184 },
  vcpus: { max: 224 },
  volume_count: { max: 114 },
  volume_size: { max: 490 }
});

const DEFAULT_RESOURCE_DETAILS = Object.freeze({
  instance_types: [
    { name: "p1-1.5gb", vcpus: 1, ram: 1536, required_volume_count: 1, required_volume_size: 8 },
    { name: "p2-3gb", vcpus: 2, ram: 3072, required_volume_count: 1, required_volume_size: 10 },
    { name: "p4-6gb", vcpus: 4, ram: 6144, required_volume_count: 0, required_volume_size: 0 },
    { name: "c64-256gb-10", vcpus: 64, ram: 253952, required_volume_count: 0, required_volume_size: 0 }
  ]
});

describe("ClusterEditor", () => {
  it("ramGbUsed", () => {
    const clusterEditorWrapper = getDefaultClusterEditorWrapper();

    // used = 6 + 3 + 1.5 * 5 GB = 16.5 GB
    expect(clusterEditorWrapper.vm.ramGbUsed).toBe(16.5);
  });

  it("ramGbMax", () => {
    const clusterEditorWrapper = getDefaultClusterEditorWrapper();

    // available = 221184 MB = 216 GB
    expect(clusterEditorWrapper.vm.ramGbMax).toBe(216);
  });

  it("vcpuUsed", () => {
    const clusterEditorWrapper = getDefaultClusterEditorWrapper();

    // used = 4 + 2 + 1 * 5
    expect(clusterEditorWrapper.vm.vcpuUsed).toBe(11);
  });

  it("vcpuMax", () => {
    const clusterEditorWrapper = getDefaultClusterEditorWrapper();

    // available = 224
    expect(clusterEditorWrapper.vm.vcpuMax).toBe(224);
  });

  it("volumeCountUsed", () => {
    const clusterEditorWrapper = getDefaultClusterEditorWrapper();

    // used = 3 (storage volumes) + 1 (login) + 5 (node)
    expect(clusterEditorWrapper.vm.volumeCountUsed).toBe(9);
  });

  it("volumeCountMax", () => {
    const clusterEditorWrapper = getDefaultClusterEditorWrapper();

    // available = 114
    expect(clusterEditorWrapper.vm.volumeCountMax).toBe(114);
  });

  it("volumeSizeUsed", () => {
    const clusterEditorWrapper = getDefaultClusterEditorWrapper();

    // used = 100 + 50 + 20.6 (storage volumes) + 10 (login) + 5 * 8 (node)
    expect(clusterEditorWrapper.vm.volumeSizeUsed).toBe(220.6);
  });

  it("volumeSizeMax", () => {
    const clusterEditorWrapper = getDefaultClusterEditorWrapper();

    // available = 490
    expect(clusterEditorWrapper.vm.volumeSizeMax).toBe(490);
  });

  const getDefaultClusterEditorWrapper = () => {
    return mount(ClusterEditor, {
      localVue,
      router,
      vuetify,
      propsData: {
        magicCastle: cloneDeep(DEFAULT_MAGIC_CASTLE),
        possibleResources: cloneDeep(DEFAULT_POSSIBLE_RESOURCES),
        quotas: cloneDeep(DEFAULT_QUOTAS),
        resourceDetails: cloneDeep(DEFAULT_RESOURCE_DETAILS),
        loading: false,
        hostname: "test1.calculquebec.cloud",
        existingCluster: true
      }
    });
  };
});
