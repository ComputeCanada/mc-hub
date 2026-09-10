import { shallowMount } from "@vue/test-utils";
import AccountDropdown from "@/components/ui/AccountDropdown";
import CloudProviderInput from "@/components/ui/CloudProviderInput";
import ProjectMembership from "@/components/ui/ProjectMembership";
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
    stubs: { "v-menu": { template: "<div><slot /></div>" } },
  });
  await new Promise((resolve) => setTimeout(resolve, 0));
  await wrapper.vm.$nextTick();
  expect(wrapper.text()).toContain("Projects");
});

test.each(["aws", "openstack"])("agent pool selection is absent on %s registration", async (provider) => {
  const wrapper = shallowMount(CloudProviderInput);
  await wrapper.setData({ newProject: { name: "personal", provider, env: {}, agent_pool_name: "private" } });
  expect(wrapper.find('[label="Agent Pool Name (optional)"]').exists()).toBe(false);
  await wrapper.vm.add();
  expect(ProjectRepository.post.mock.calls[0][0].agent_pool_name).toBeUndefined();
});

test.each(["aws", "openstack"])("agent pool editing is absent for %s", async (provider) => {
  const wrapper = shallowMount(ProjectMembership, { propsData: { id: 1, admin: true } });
  await wrapper.setData({ project: { provider, members: [], admins: [] }, agentPoolName: "private" });
  expect(wrapper.find('[label="Agent Pool Name"]').exists()).toBe(false);
  await wrapper.vm.save();
  expect(ProjectRepository.patch.mock.calls[0][1].agent_pool_name).toBeUndefined();
});
