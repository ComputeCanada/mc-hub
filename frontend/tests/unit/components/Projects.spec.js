import { mount, flushPromises } from "@vue/test-utils";
import { createAppVuetify } from "@/plugins/vuetify";
import Projects from "@/views/Projects";
import UserRepository from "@/repositories/UserRepository";
import CloudProviderInput from "@/components/ui/CloudProviderInput";
import ProjectEditor from "@/components/ui/ProjectEditor";
import ProjectMembership from "@/components/ui/ProjectMembership";
import ProjectNotifications from "@/components/ui/ProjectNotifications";
import AWSCredentials from "@/components/ui/AWSCredentials";
import OpenStackCredentials from "@/components/ui/OpenStackCredentials";
import ProjectRepository from "@/repositories/ProjectRepository";
import Repository from "@/repositories/Repository";

jest.mock("@/repositories/ProjectRepository", () => ({
  getAll: jest.fn(),
  delete: jest.fn(),
  get: jest.fn(),
  patch: jest.fn(),
  post: jest.fn(),
  openstackClouds: jest.fn(),
  openstackSubnets: jest.fn(),
  awsRegions: jest.fn(),
}));
jest.mock("@/repositories/Repository", () => ({ get: jest.fn(), put: jest.fn(), delete: jest.fn() }));
jest.mock("@/repositories/UserRepository", () => ({ getCurrent: jest.fn(), setDefaultProject: jest.fn() }));
const projects = [
  { id: 11, name: "Owned", provider: "aws", nb_clusters: 0, admin: true, can_manage_notifications: true },
  { id: 22, name: "Member", provider: "openstack", nb_clusters: 2, admin: false, can_manage_notifications: false },
  { id: 33, name: "Busy", provider: "aws", nb_clusters: 1, admin: true, can_manage_notifications: false },
];
let wrapper, host, warn;
beforeEach(() => {
  jest.clearAllMocks();
  ProjectRepository.getAll.mockResolvedValue({ data: projects });
  ProjectRepository.delete.mockResolvedValue({});
  UserRepository.getCurrent.mockResolvedValue({ data: { default_project_id: 22 } });
  ProjectRepository.get.mockResolvedValue({
    data: { provider: "aws", region: "ca-central-1", nb_clusters: 1, members: ["alice"], admins: [] },
  });
  ProjectRepository.post.mockResolvedValue({});
  ProjectRepository.patch.mockResolvedValue({});
  ProjectRepository.openstackClouds.mockResolvedValue({
    data: { clouds: [{ name: "Research", auth_url: "https://cloud.example/v3" }] },
  });
  ProjectRepository.openstackSubnets.mockResolvedValue({ data: { subnets: [{ id: "private", name: "Private" }] } });
  ProjectRepository.awsRegions.mockResolvedValue({ data: { regions: ["ca-central-1"] } });
  Repository.get.mockResolvedValue({ data: { configured: false } });
  Repository.put.mockResolvedValue({});
  Repository.delete.mockResolvedValue({});
  host = document.createElement("div");
  document.body.append(host);
  warn = jest.spyOn(console, "warn");
});
afterEach(() => {
  wrapper?.unmount();
  host.remove();
  document.querySelectorAll(".v-overlay-container").forEach((node) => node.remove());
  expect(warn).not.toHaveBeenCalled();
  jest.restoreAllMocks();
});
async function render() {
  wrapper = mount(Projects, { attachTo: host, global: { plugins: [createAppVuetify()] } });
  await flushPromises();
}
async function open(label) {
  await wrapper.get(`button[aria-label="${label}"]`).trigger("click");
  await flushPromises();
}
async function click(text) {
  const button = [...document.querySelectorAll("button")].find((node) => node.textContent.trim() === text);
  expect(button).toBeDefined();
  button.click();
  await flushPromises();
}
function field(component, label) {
  return component.findAllComponents({ name: "VTextField" }).find((input) => input.props("label") === label);
}

test("renders current table columns and enforces row permissions", async () => {
  await render();
  expect(wrapper.findAll("thead th").map((cell) => cell.text())).toEqual([
    "Default",
    "Name",
    "Provider",
    "# Clusters",
    "",
  ]);
  const rows = wrapper.findAll("tbody tr");
  expect(rows).toHaveLength(3);
  expect(rows[0].text()).toContain("Owned");
  expect(rows[1].get('button[aria-label="Edit"]').element.disabled).toBe(true);
  expect(rows[1].get('button[aria-label="Members"]').element.disabled).toBe(true);
  expect(rows[1].find('button[aria-label="Notifications"]').exists()).toBe(false);
  expect(rows[1].text()).toContain("not owner");
  expect(rows[2].get('button[aria-label="Delete Busy"]').element.disabled).toBe(true);
  expect(rows[1].get('input[type="checkbox"]').element.checked).toBe(true);
});

test("creation through the screen refreshes projects after saving nested credentials", async () => {
  await render();
  await click("Add Project");
  const dialog = wrapper.findComponent(CloudProviderInput);
  const credentials = dialog.findComponent(OpenStackCredentials);
  await credentials.findComponent({ name: "VSelect" }).setValue("https://cloud.example/v3");
  await field(credentials, "OpenStack application credential ID").get("input").setValue("credential");
  await field(credentials, "OpenStack application credential secret").get("input").setValue("secret");
  await click("refresh");
  await credentials.findAllComponents({ name: "VSelect" })[1].setValue("private");
  await field(dialog, "Project name").get("input").setValue("research");
  ProjectRepository.getAll.mockResolvedValueOnce({ data: [...projects, { id: 44, name: "research" }] });
  await click("Add");
  expect(ProjectRepository.post).toHaveBeenCalledWith(expect.objectContaining({ name: "research" }));
  expect(ProjectRepository.getAll).toHaveBeenCalledTimes(2);
  expect(wrapper.text()).toContain("research");
  expect(dialog.vm.dialog).toBe(false);
});

test("editing the correct project refreshes the screen after a successful save", async () => {
  await render();
  await open("Edit");
  expect(ProjectRepository.get).toHaveBeenCalledWith(11);
  const dialog = wrapper.findComponent(ProjectEditor);
  const credentials = dialog.findComponent(AWSCredentials);
  await field(credentials, "AWS access key ID").get("input").setValue("access");
  await field(credentials, "AWS secret access key").get("input").setValue("secret");
  await click("Save");
  expect(ProjectRepository.patch).toHaveBeenCalledWith(
    11,
    expect.objectContaining({
      env: expect.objectContaining({ AWS_ACCESS_KEY_ID: "access", AWS_SECRET_ACCESS_KEY: "secret" }),
    })
  );
  expect(ProjectRepository.getAll).toHaveBeenCalledTimes(2);
  expect(dialog.vm.dialog).toBe(false);
});

test("membership saves and refreshes from the correct row", async () => {
  await render();
  await open("Members");
  expect(ProjectRepository.get).toHaveBeenCalledWith(11);
  document.querySelector('input[aria-label="Admin"]').click();
  await flushPromises();
  await click("Save");
  expect(ProjectRepository.patch).toHaveBeenCalledWith(11, { add: [], del: [], add_admins: ["alice"], del_admins: [] });
  expect(ProjectRepository.getAll).toHaveBeenCalledTimes(2);
  expect(wrapper.findComponent(ProjectMembership).vm.dialog).toBe(false);
});

test("notification settings save from an authorized project row", async () => {
  await render();
  await open("Notifications");
  const dialog = wrapper.findComponent(ProjectNotifications);
  await field(dialog, "HTTPS webhook URL").get("input").setValue("https://notify.example/hook");
  await click("Save");
  expect(Repository.put).toHaveBeenCalledWith("/projects/11/notification-destination", {
    type: "webhook",
    enabled: true,
    url: "https://notify.example/hook",
  });
  expect(dialog.vm.dialog).toBe(false);
});

test("delete refreshes the list and reports API failures without removing rows", async () => {
  await render();
  ProjectRepository.delete.mockRejectedValueOnce(new Error("offline"));
  await open("Delete Owned");
  expect(wrapper.text()).toContain("Unable to delete the project");
  expect(wrapper.findAll("tbody tr")).toHaveLength(3);
  ProjectRepository.getAll.mockResolvedValueOnce({ data: projects.slice(1) });
  await open("Delete Owned");
  expect(ProjectRepository.delete).toHaveBeenCalledWith(11);
  expect(wrapper.findAll("tbody tr")).toHaveLength(2);
  expect(wrapper.text()).not.toContain("Unable to delete");
});

test("default selection uses the row ID and preserves the saved selection on failure", async () => {
  UserRepository.setDefaultProject.mockRejectedValueOnce(new Error("offline"));
  await render();
  const owned = wrapper.get('input[aria-label="Set Owned as default project"]');
  const member = wrapper.get('input[aria-label="Set Member as default project"]');
  owned.element.click();
  await flushPromises();
  expect(UserRepository.setDefaultProject).toHaveBeenCalledWith(11);
  expect(owned.element.checked).toBe(false);
  expect(member.element.checked).toBe(true);
  expect(wrapper.text()).toContain("Unable to save your default project");
  UserRepository.setDefaultProject.mockResolvedValueOnce({ data: { default_project_id: 11 } });
  await owned.trigger("keydown", { key: "Enter" });
  await flushPromises();
  expect(owned.element.checked).toBe(true);
  expect(member.element.checked).toBe(false);
  expect(wrapper.text()).not.toContain("Unable to save your default project");
});

test("failed edits keep the dialog open without refreshing the list", async () => {
  ProjectRepository.patch.mockRejectedValueOnce(new Error("offline"));
  await render();
  await open("Edit");
  await click("Save");
  expect(wrapper.findComponent(ProjectEditor).vm.dialog).toBe(true);
  expect(document.body.textContent).toContain("An error occurred while saving the project");
  expect(ProjectRepository.getAll).toHaveBeenCalledTimes(1);
});
