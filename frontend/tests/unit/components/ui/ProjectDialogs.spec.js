import { mount, flushPromises } from "@vue/test-utils";
import { createAppVuetify } from "@/plugins/vuetify";
import CloudProviderInput from "@/components/ui/CloudProviderInput";
import ProjectEditor from "@/components/ui/ProjectEditor";
import ProjectMembership from "@/components/ui/ProjectMembership";
import ProjectNotifications from "@/components/ui/ProjectNotifications";
import AWSCredentials from "@/components/ui/AWSCredentials";
import OpenStackCredentials from "@/components/ui/OpenStackCredentials";
import ProjectRepository from "@/repositories/ProjectRepository";
import Repository from "@/repositories/Repository";

jest.mock("@/repositories/ProjectRepository", () => ({
  get: jest.fn(),
  patch: jest.fn(),
  post: jest.fn(),
  openstackClouds: jest.fn(),
  openstackSubnets: jest.fn(),
  awsRegions: jest.fn(),
}));
jest.mock("@/repositories/Repository", () => ({ get: jest.fn(), put: jest.fn(), delete: jest.fn() }));
let wrapper, host, warn;
beforeEach(() => {
  jest.clearAllMocks();
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
async function render(component, props = {}) {
  wrapper = mount(component, { props, attachTo: host, global: { plugins: [createAppVuetify()] } });
  await wrapper.get("button").trigger("click");
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

test("registration propagates nested OpenStack credentials and the selected subnet to the API", async () => {
  await render(CloudProviderInput);
  const credentials = wrapper.findComponent(OpenStackCredentials);
  await credentials.findComponent({ name: "VSelect" }).setValue("https://cloud.example/v3");
  await field(credentials, "OpenStack application credential ID").get("input").setValue("credential");
  await field(credentials, "OpenStack application credential secret").get("input").setValue("secret");
  await click("refresh");
  const subnet = credentials.findAllComponents({ name: "VSelect" })[1];
  await subnet.setValue("private");
  await field(wrapper, "Project name").get("input").setValue("research");
  await click("Add");
  expect(ProjectRepository.post).toHaveBeenCalledWith(
    expect.objectContaining({
      name: "research",
      env: {
        OS_AUTH_URL: "https://cloud.example/v3",
        OS_APPLICATION_CREDENTIAL_ID: "credential",
        OS_APPLICATION_CREDENTIAL_SECRET: "secret",
        OS_SUBNET_ID: "private",
      },
    })
  );
  expect(wrapper.vm.dialog).toBe(false);
});

test("project editing keeps the locked AWS region while nested credentials change", async () => {
  await render(ProjectEditor, { id: 1, admin: true });
  const credentials = wrapper.findComponent(AWSCredentials);
  expect(credentials.findComponent({ name: "VSelect" }).props("disabled")).toBe(true);
  await field(credentials, "AWS access key ID").get("input").setValue("access");
  await field(credentials, "AWS secret access key").get("input").setValue("secret");
  await click("Save");
  expect(ProjectRepository.patch).toHaveBeenCalledWith(
    1,
    expect.objectContaining({
      env: {
        AWS_ACCESS_KEY_ID: "access",
        AWS_SECRET_ACCESS_KEY: "secret",
        AWS_SESSION_TOKEN: "",
        AWS_DEFAULT_REGION: "ca-central-1",
      },
    })
  );
});

test("membership activator, admin checkbox and cancel/reopen work with real dialogs", async () => {
  await render(ProjectMembership, { id: 1, admin: true });
  const checkbox = document.querySelector('input[aria-label="Admin"]');
  expect(checkbox).not.toBeNull();
  checkbox.click();
  await flushPromises();
  await click("Save");
  expect(ProjectRepository.patch).toHaveBeenCalledWith(1, { add: [], del: [], add_admins: ["alice"], del_admins: [] });
  await wrapper.get("button").trigger("click");
  await flushPromises();
  expect(wrapper.vm.entries[0].isAdmin).toBe(false);
  await click("Cancel");
  expect(wrapper.vm.dialog).toBe(false);
});

test("notification activator opens the real form and saves a valid destination", async () => {
  await render(ProjectNotifications, { id: 1 });
  await field(wrapper, "HTTPS webhook URL").get("input").setValue("https://notify.example/hook");
  await flushPromises();
  await click("Save");
  expect(Repository.put).toHaveBeenCalledWith("/projects/1/notification-destination", {
    type: "webhook",
    enabled: true,
    url: "https://notify.example/hook",
  });
  expect(wrapper.vm.dialog).toBe(false);
});
