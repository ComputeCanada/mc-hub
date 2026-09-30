import { flushPromises } from "@vue/test-utils";
import { shallowMountWithVuetify as shallowMount, cleanupMounts } from "../../../helpers/mount";
import OpenStackSubnet from "@/components/ui/OpenStackSubnet";
import ProjectRepository from "@/repositories/ProjectRepository";

jest.mock("@/repositories/ProjectRepository", () => ({ openstackSubnets: jest.fn() }));

it("displays subnet names with credentials and emits the selected UUID", async () => {
  const env = { OS_AUTH_URL: "https://cloud.example.org", OS_APPLICATION_CREDENTIAL_SECRET: "secret" };
  ProjectRepository.openstackSubnets.mockResolvedValue({
    data: { subnets: [{ id: "subnet-a", name: "Private subnet" }] },
  });
  const wrapper = shallowMount(OpenStackSubnet, {
    props: { modelValue: env },
    global: { renderStubDefaultSlot: true },
  });
  await wrapper.vm.loadSubnets();
  expect(ProjectRepository.openstackSubnets).toHaveBeenCalledWith({ env });
  expect(wrapper.vm.subnets).toEqual([{ id: "subnet-a", name: "Private subnet" }]);
  expect(wrapper.findComponent("v-select-stub").props("itemTitle")).toBe("name");
  expect(wrapper.findComponent("v-select-stub").props("itemValue")).toBe("id");
  await wrapper.findComponent("v-select-stub").setValue("subnet-a");
  expect(wrapper.emitted("update:modelValue").pop()[0]).toEqual({ ...env, OS_SUBNET_ID: "subnet-a" });
  wrapper.unmount();
});

it("clears selection and ignores pending results when credentials change", async () => {
  let resolve;
  ProjectRepository.openstackSubnets.mockReturnValue(
    new Promise((r) => {
      resolve = r;
    })
  );
  const wrapper = shallowMount(OpenStackSubnet, {
    props: { modelValue: { OS_APPLICATION_CREDENTIAL_SECRET: "old", OS_SUBNET_ID: "subnet-old" } },
    global: { renderStubDefaultSlot: true },
  });
  const request = wrapper.vm.loadSubnets();
  await wrapper.setProps({ modelValue: { OS_APPLICATION_CREDENTIAL_SECRET: "new", OS_SUBNET_ID: "subnet-old" } });
  resolve({ data: { subnets: [{ id: "subnet-old", name: "Old subnet" }] } });
  await request;
  expect(wrapper.vm.subnets).toEqual([]);
  expect(wrapper.emitted("update:modelValue").pop()[0]).toEqual({ OS_APPLICATION_CREDENTIAL_SECRET: "new" });
  wrapper.unmount();
});

it("shows discovery errors and allows retry", async () => {
  ProjectRepository.openstackSubnets.mockRejectedValue(new Error("failed"));
  const wrapper = shallowMount(OpenStackSubnet, { props: { modelValue: {} }, global: { renderStubDefaultSlot: true } });
  await wrapper.vm.loadSubnets();
  expect(wrapper.vm.error).toContain("Unable to load OpenStack subnets");
  expect(wrapper.vm.loading).toBe(false);
  ProjectRepository.openstackSubnets.mockResolvedValue({ data: { subnets: [] } });
  await wrapper.vm.loadSubnets();
  expect(wrapper.vm.error).toBe("");
  wrapper.unmount();
});

it("preserves a selected UUID when named subnet options refresh", async () => {
  ProjectRepository.openstackSubnets.mockResolvedValue({ data: { subnets: [{ id: "subnet-a", name: "Renamed" }] } });
  const wrapper = shallowMount(OpenStackSubnet, {
    props: { modelValue: { OS_SUBNET_ID: "subnet-a" } },
    global: { renderStubDefaultSlot: true },
  });
  await wrapper.vm.loadSubnets();
  expect(wrapper.emitted("update:modelValue")).toBeUndefined();
  wrapper.unmount();
});

it("keeps the saved project subnet selected while loading and refreshing options", async () => {
  let resolve;
  ProjectRepository.openstackSubnets.mockReturnValue(new Promise((r) => (resolve = r)));
  const wrapper = shallowMount(OpenStackSubnet, {
    props: { projectId: 1, modelValue: { OS_SUBNET_ID: "saved-subnet" } },
    global: { renderStubDefaultSlot: true },
  });
  const select = () => wrapper.findComponent("v-select-stub");
  expect(select().props("modelValue")).toBe("saved-subnet");
  expect(select().props("items")).toContainEqual({ id: "saved-subnet", name: "saved-subnet" });
  resolve({ data: { subnets: [{ id: "saved-subnet", name: "Private network" }] } });
  await flushPromises();
  expect(select().props("items")).toEqual([{ id: "saved-subnet", name: "Private network" }]);
  expect(select().props("modelValue")).toBe("saved-subnet");
  ProjectRepository.openstackSubnets.mockResolvedValue({ data: { subnets: [] } });
  await wrapper.vm.loadSubnets();
  expect(select().props("modelValue")).toBe("saved-subnet");
  expect(wrapper.emitted("update:modelValue")).toBeUndefined();
  await wrapper.setProps({ modelValue: { OS_SUBNET_ID: "saved-subnet", OS_APPLICATION_CREDENTIAL_SECRET: "updated" } });
  expect(wrapper.emitted("update:modelValue")).toBeUndefined();
  wrapper.unmount();
});
afterEach(cleanupMounts);
