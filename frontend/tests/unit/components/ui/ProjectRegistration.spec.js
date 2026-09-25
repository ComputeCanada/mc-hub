import { flushPromises } from "@vue/test-utils";
import { shallowMountWithVuetify as shallowMount, cleanupMounts } from "../../../helpers/mount";
import AccountDropdown from "@/components/ui/AccountDropdown";
import CloudProviderInput from "@/components/ui/CloudProviderInput";
import ProjectEditor from "@/components/ui/ProjectEditor";
import ProjectRepository from "@/repositories/ProjectRepository";

jest.mock("@/repositories/UserRepository", () => ({
  getCurrent: jest.fn().mockResolvedValue({ data: { username: "alice", usertype: "saml", is_admin: false } }),
}));
jest.mock("@/repositories/ProjectRepository", () => ({
  post: jest.fn().mockResolvedValue({}),
  patch: jest.fn().mockResolvedValue({}),
}));

beforeEach(() => jest.clearAllMocks());

test("regular users can reach Projects from their account menu", async () => {
  const wrapper = shallowMount(AccountDropdown, {
    global: { renderStubDefaultSlot: true, stubs: { "v-menu": { template: "<div><slot /></div>" } } },
  });
  await flushPromises();
  await wrapper.vm.$nextTick();
  expect(wrapper.text()).toContain("Projects");
});

test.each(["aws", "openstack"])("agent pool selection is absent on %s registration", async (provider) => {
  const wrapper = shallowMount(CloudProviderInput, { global: { renderStubDefaultSlot: true } });
  await wrapper.setData({ newProject: { name: "personal", provider, env: {}, agent_pool_name: "private" } });
  expect(wrapper.find('[label="Agent Pool Name (optional)"]').exists()).toBe(false);
  await wrapper.vm.add();
  expect(ProjectRepository.post.mock.calls[0][0].agent_pool_name).toBeUndefined();
});

test.each(["aws", "openstack"])("agent pool editing is absent for %s", async (provider) => {
  const wrapper = shallowMount(ProjectEditor, {
    props: { id: 1, admin: true },
    global: { renderStubDefaultSlot: true },
  });
  await wrapper.setData({
    project: { provider },
    agentPoolName: "private",
    env: { OS_SUBNET_ID: "new-subnet" },
  });
  expect(wrapper.find('[label="Agent Pool Name"]').exists()).toBe(false);
  await wrapper.vm.save();
  expect(ProjectRepository.patch.mock.calls[0][1].agent_pool_name).toBeUndefined();
});

test("OpenStack credentials can be updated without selecting a cloud", async () => {
  const wrapper = shallowMount(ProjectEditor, {
    props: { id: 1, admin: true },
    global: { renderStubDefaultSlot: true },
  });
  const env = { OS_APPLICATION_CREDENTIAL_ID: "a".repeat(32), OS_APPLICATION_CREDENTIAL_SECRET: "s".repeat(86) };
  await wrapper.setData({ project: { provider: "openstack", members: [], admins: [] }, env });
  await wrapper.vm.save();
  expect(ProjectRepository.patch).toHaveBeenCalledWith(1, expect.objectContaining({ env }));
});

test("OpenStack subnet can be saved with credentials left empty", async () => {
  const wrapper = shallowMount(ProjectEditor, {
    props: { id: 1, admin: true },
    global: { renderStubDefaultSlot: true },
  });
  await wrapper.setData({
    project: { provider: "openstack", members: [], admins: [], subnet_id: "old-subnet" },
    env: { OS_APPLICATION_CREDENTIAL_ID: "", OS_APPLICATION_CREDENTIAL_SECRET: "", OS_SUBNET_ID: "new-subnet" },
  });
  await wrapper.vm.save();
  expect(ProjectRepository.patch).toHaveBeenCalledWith(
    1,
    expect.objectContaining({ env: { OS_SUBNET_ID: "new-subnet" } })
  );
});
afterEach(cleanupMounts);
