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
  projects: ["arbutus:training"],
  public_keys: [],
});

const DEFAULT_MAGIC_CASTLE = Object.freeze({
  cluster_name: "",
  domain: "calculquebec.cloud",
  image: "CentOS-7-x64-2021-11",
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
  image: ["centos7", "centos7-updated", "CentOS-7-x64-2021-11", "CentOS-8-x64-2019-11", "CentOS-7-x64-2019-01"],
  tag_types: {"mgmt": ["p4-6gb", "c2-7.5gb-31"], "login": ["p2-3gb", "p4-6gb"], "node": ["p2-3gb", "p4-6gb"]},
  "types": ["p1-1.5gb", "p2-3gb", "p4-6gb"],
  volumes: {},
  domain: ["calculquebec.cloud", "c3.ca"]
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


async function getDefaultClusterEditorWrapper(existingCluster=true, hostname="test1.calculquebec.cloud") {
  let wrapper = mount(ClusterEditor, {
    localVue,
    router,
    vuetify,
    propsData: {
      specs: cloneDeep(DEFAULT_MAGIC_CASTLE),
      existingCluster: existingCluster,
      hostname: hostname
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

  it("magicCastleGuestPasswordNonExisting", async () => {
    const clusterEditorWrapperNew = await getDefaultClusterEditorWrapper(false);
    expect(clusterEditorWrapperNew.vm.specs.guest_passwd.length).toBe(12);
  });

  it("magicCastleGuestPasswordExisting", async () => {
    const clusterEditorWrapperExisting = await getDefaultClusterEditorWrapper(true);
    expect(clusterEditorWrapperExisting.vm.specs.guest_passwd.length).toBe(0);
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
