import { shallowMount } from "@vue/test-utils";
import OpenStackCloud from "@/components/ui/OpenStackCloud";
import OpenStackCredentials from "@/components/ui/OpenStackCredentials";
import CloudProviderInput from "@/components/ui/CloudProviderInput";
import ProjectMembership from "@/components/ui/ProjectMembership";
import ProjectRepository from "@/repositories/ProjectRepository";

jest.mock("@/repositories/ProjectRepository", () => ({ openstackClouds: jest.fn() }));
const clouds = [{ name: "Research Cloud", auth_url: "https://cloud.example.org/v3" }];
const settle = () => new Promise((resolve) => setTimeout(resolve, 0));

beforeEach(() => {
  jest.clearAllMocks();
  ProjectRepository.openstackClouds.mockResolvedValue({ data: { clouds } });
});

test("shows cloud names and emits the approved URL", async () => {
  const wrapper = shallowMount(OpenStackCloud, { stubs: ["v-select"] });
  await settle();
  const select = wrapper.find("v-select-stub");
  expect(select.attributes("item-text")).toBe("name");
  expect(select.attributes("item-value")).toBe("auth_url");
  expect(wrapper.vm.clouds).toEqual(clouds);
  select.vm.$emit("change", clouds[0].auth_url);
  expect(wrapper.emitted("input")[0]).toEqual([clouds[0].auth_url]);
});

test("does not display an arbitrary URL as the selected cloud", async () => {
  const wrapper = shallowMount(OpenStackCloud, { propsData: { value: "https://unapproved.example.org" } });
  await settle();
  expect(wrapper.vm.selectedValue).toBeNull();
  await wrapper.setProps({ value: clouds[0].auth_url });
  expect(wrapper.vm.selectedValue).toBe(clouds[0].auth_url);
});

test("explains an empty operator list", async () => {
  ProjectRepository.openstackClouds.mockResolvedValue({ data: { clouds: [] } });
  const wrapper = shallowMount(OpenStackCloud);
  await settle();
  expect(wrapper.text()).toContain("No OpenStack clouds are available");
});

test("can retry after a list-loading failure", async () => {
  ProjectRepository.openstackClouds.mockRejectedValueOnce(new Error("offline"));
  const wrapper = shallowMount(OpenStackCloud);
  await settle();
  expect(wrapper.text()).toContain("Unable to load approved OpenStack clouds");
  await wrapper.vm.loadClouds();
  expect(wrapper.vm.error).toBe("");
  expect(wrapper.vm.clouds).toEqual(clouds);
});

test("creation selects a cloud while editing displays its name read-only", async () => {
  const create = shallowMount(CloudProviderInput, { stubs: { OpenStackCredentials } });
  expect(create.findComponent(OpenStackCloud).exists()).toBe(true);
  expect(create.find('[label="OS_AUTH_URL"]').exists()).toBe(false);
  const edit = shallowMount(ProjectMembership, {
    propsData: { id: 1, admin: true },
    stubs: { OpenStackCredentials },
  });
  await edit.setData({ project: { provider: "openstack", cloud_name: "Research Cloud" } });
  expect(edit.findComponent(OpenStackCloud).exists()).toBe(false);
  expect(edit.findComponent(OpenStackCredentials).props("cloudName")).toBe("Research Cloud");
  const cloud = edit.find('[label="OpenStack cloud"]');
  expect(cloud.attributes("value")).toBe("Research Cloud");
  expect(cloud.attributes("readonly")).toBeDefined();
  expect(edit.find('[label="OS_AUTH_URL"]').exists()).toBe(false);
});
