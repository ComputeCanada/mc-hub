import Vue from "vue";
import Vuetify from "vuetify";
import { shallowMount } from "@vue/test-utils";
import OpenStackSubnet from "@/components/ui/OpenStackSubnet";
import ProjectRepository from "@/repositories/ProjectRepository";

Vue.use(Vuetify);
jest.mock("@/repositories/ProjectRepository", () => ({ openstackSubnets: jest.fn() }));

it("displays subnet names with credentials and emits the selected UUID", async () => {
  const env = { OS_AUTH_URL: "https://cloud.example.org", OS_APPLICATION_CREDENTIAL_SECRET: "secret" };
  ProjectRepository.openstackSubnets.mockResolvedValue({
    data: { subnets: [{ id: "subnet-a", name: "Private subnet" }] },
  });
  const wrapper = shallowMount(OpenStackSubnet, { propsData: { value: env } });
  await wrapper.vm.loadSubnets();
  expect(ProjectRepository.openstackSubnets).toHaveBeenCalledWith({ env });
  expect(wrapper.vm.subnets).toEqual([{ id: "subnet-a", name: "Private subnet" }]);
  expect(wrapper.find("v-select-stub").props("itemText")).toBe("name");
  expect(wrapper.find("v-select-stub").props("itemValue")).toBe("id");
  wrapper.find("v-select-stub").vm.$emit("change", "subnet-a");
  expect(wrapper.emitted("input").pop()[0]).toEqual({ ...env, OS_SUBNET_ID: "subnet-a" });
  wrapper.destroy();
});

it("clears selection and ignores pending results when credentials change", async () => {
  let resolve;
  ProjectRepository.openstackSubnets.mockReturnValue(
    new Promise((r) => {
      resolve = r;
    })
  );
  const wrapper = shallowMount(OpenStackSubnet, {
    propsData: { value: { OS_APPLICATION_CREDENTIAL_SECRET: "old", OS_SUBNET_ID: "subnet-old" } },
  });
  const request = wrapper.vm.loadSubnets();
  await wrapper.setProps({ value: { OS_APPLICATION_CREDENTIAL_SECRET: "new", OS_SUBNET_ID: "subnet-old" } });
  resolve({ data: { subnets: [{ id: "subnet-old", name: "Old subnet" }] } });
  await request;
  expect(wrapper.vm.subnets).toEqual([]);
  expect(wrapper.emitted("input").pop()[0]).toEqual({ OS_APPLICATION_CREDENTIAL_SECRET: "new" });
  wrapper.destroy();
});

it("shows discovery errors and allows retry", async () => {
  ProjectRepository.openstackSubnets.mockRejectedValue(new Error("failed"));
  const wrapper = shallowMount(OpenStackSubnet, { propsData: { value: {} } });
  await wrapper.vm.loadSubnets();
  expect(wrapper.vm.error).toContain("Unable to load OpenStack subnets");
  expect(wrapper.vm.loading).toBe(false);
  ProjectRepository.openstackSubnets.mockResolvedValue({ data: { subnets: [] } });
  await wrapper.vm.loadSubnets();
  expect(wrapper.vm.error).toBe("");
  wrapper.destroy();
});

it("preserves a selected UUID when named subnet options refresh", async () => {
  ProjectRepository.openstackSubnets.mockResolvedValue({ data: { subnets: [{ id: "subnet-a", name: "Renamed" }] } });
  const wrapper = shallowMount(OpenStackSubnet, { propsData: { value: { OS_SUBNET_ID: "subnet-a" } } });
  await wrapper.vm.loadSubnets();
  expect(wrapper.emitted("input")).toBeUndefined();
  wrapper.destroy();
});

it("keeps the saved project subnet selected while loading and refreshing options", async () => {
  let resolve;
  ProjectRepository.openstackSubnets.mockReturnValue(new Promise((r) => (resolve = r)));
  const wrapper = shallowMount(OpenStackSubnet, {
    propsData: { projectId: 1, value: { OS_SUBNET_ID: "saved-subnet" } },
  });
  const select = () => wrapper.find("v-select-stub");
  expect(select().props("value")).toBe("saved-subnet");
  expect(select().props("items")).toContainEqual({ id: "saved-subnet", name: "saved-subnet" });
  resolve({ data: { subnets: [{ id: "saved-subnet", name: "Private network" }] } });
  await new Promise((r) => setTimeout(r, 0));
  expect(select().props("items")).toEqual([{ id: "saved-subnet", name: "Private network" }]);
  expect(select().props("value")).toBe("saved-subnet");
  ProjectRepository.openstackSubnets.mockResolvedValue({ data: { subnets: [] } });
  await wrapper.vm.loadSubnets();
  expect(select().props("value")).toBe("saved-subnet");
  expect(wrapper.emitted("input")).toBeUndefined();
  await wrapper.setProps({ value: { OS_SUBNET_ID: "saved-subnet", OS_APPLICATION_CREDENTIAL_SECRET: "updated" } });
  expect(wrapper.emitted("input")).toBeUndefined();
  wrapper.destroy();
});
