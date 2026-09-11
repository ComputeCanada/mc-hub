import Vue from "vue";
import Vuetify from "vuetify";
import { shallowMount } from "@vue/test-utils";
import ProjectMembership from "@/components/ui/ProjectMembership";
import ProjectEditor from "@/components/ui/ProjectEditor";
import ProjectRepository from "@/repositories/ProjectRepository";

Vue.use(Vuetify);

jest.mock("@/repositories/ProjectRepository", () => ({
  get: jest.fn(),
  patch: jest.fn(),
}));

const project = {
  provider: "aws",
  members: ["alice", "bob", "carol"],
  admins: ["alice", "carol"],
  region: "ca-central-1",
  max_instance_hourly_price: "0.25",
};
const flush = () => new Promise(jest.requireActual("timers").setImmediate);

beforeEach(() => {
  jest.clearAllMocks();
  ProjectRepository.get.mockResolvedValue({ data: project });
  ProjectRepository.patch.mockResolvedValue({});
});

test("members dialog saves membership and role changes without changing cloud settings", async () => {
  const wrapper = shallowMount(ProjectMembership, { propsData: { id: 1, admin: true } });
  await wrapper.setData({ dialog: true });
  await flush();
  expect(ProjectRepository.get).toHaveBeenCalledWith(1);
  expect(wrapper.find('[label="Maximum instance price (USD/hour)"]').exists()).toBe(false);
  wrapper.vm.removeMember("carol");
  wrapper.vm.entries.find((entry) => entry.username === "bob").isAdmin = true;
  await wrapper.setData({ newMember: "dave", newMemberIsAdmin: false });
  wrapper.vm.addMember();
  await wrapper.vm.save();
  expect(ProjectRepository.patch).toHaveBeenCalledWith(1, {
    add: ["dave"],
    del: ["carol"],
    add_admins: ["bob"],
    del_admins: ["carol"],
  });
  expect(wrapper.emitted("saved")).toHaveLength(1);
  expect(wrapper.vm.dialog).toBe(false);
});

test("cancel discards membership edits and reopening reloads members", async () => {
  const wrapper = shallowMount(ProjectMembership, { propsData: { id: 1, admin: true } });
  await wrapper.setData({ dialog: true });
  await flush();
  wrapper.vm.removeMember("bob");
  wrapper.vm.close();
  await flush();
  expect(ProjectRepository.patch).not.toHaveBeenCalled();
  await wrapper.setData({ dialog: true });
  await flush();
  expect(wrapper.vm.entries.map((entry) => entry.username)).toEqual(project.members);
});

test("failed membership saves keep the edits and show the server error", async () => {
  ProjectRepository.patch.mockRejectedValue({ response: { data: { message: "Unable to update members" } } });
  const wrapper = shallowMount(ProjectMembership, { propsData: { id: 1, admin: true } });
  await wrapper.setData({ dialog: true });
  await flush();
  wrapper.vm.removeMember("bob");
  await wrapper.vm.save();
  expect(wrapper.vm.dialog).toBe(true);
  expect(wrapper.vm.errorMessage).toBe("Unable to update members");
  expect(wrapper.emitted("saved")).toBeUndefined();
});

test("project settings save independently of membership", async () => {
  const wrapper = shallowMount(ProjectEditor, { propsData: { id: 1, admin: true } });
  await wrapper.setData({ project, maxInstanceHourlyPrice: "0.50" });
  expect(wrapper.find('[label="Add a member"]').exists()).toBe(false);
  await wrapper.vm.save();
  expect(ProjectRepository.patch).toHaveBeenCalledWith(1, { max_instance_hourly_price: "0.50" });
});
