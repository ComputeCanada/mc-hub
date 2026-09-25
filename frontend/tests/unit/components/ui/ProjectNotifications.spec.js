import { flushPromises } from "@vue/test-utils";
import { mountWithVuetify as mount, cleanupMounts } from "../../../helpers/mount";
import ProjectNotifications from "@/components/ui/ProjectNotifications";
import Repository from "@/repositories/Repository";

jest.mock("@/repositories/Repository", () => ({ get: jest.fn(), put: jest.fn(), delete: jest.fn() }));
const flush = flushPromises;
let wrapper;
beforeEach(() => {
  jest.clearAllMocks();
  Repository.get.mockResolvedValue({ data: { configured: true, type: "webhook", enabled: true, has_token: true } });
  Repository.put.mockResolvedValue({ data: { configured: true } });
  Repository.delete.mockResolvedValue({ data: { configured: false } });
  wrapper = mount(ProjectNotifications, {
    props: { id: 12 },
    global: {
      // Keep the dialog open for these form tests; validate with real inputs.
      stubs: { VDialog: { template: "<div><slot /></div>" }, ConfirmDialog: true },
    },
  });
});
afterEach(() => wrapper.unmount());

async function open() {
  await wrapper.setData({ dialog: true });
  await flush();
}

test("stored credentials remain blank and unchanged when omitted", async () => {
  await open();
  expect(Repository.get).toHaveBeenCalledWith("/projects/12/notification-destination");
  expect(wrapper.vm.url).toBe("");
  expect(wrapper.vm.token).toBe("");
  expect(wrapper.vm.hasToken).toBe(true);
  await wrapper.vm.save();
  expect(Repository.put).toHaveBeenCalledWith("/projects/12/notification-destination", {
    type: "webhook",
    enabled: true,
  });
});

test("replacement credentials are saved and cleared when the dialog closes", async () => {
  await open();
  await wrapper.setData({ url: "https://example.com/secret", token: "token-secret" });
  await wrapper.vm.save();
  await wrapper.vm.$nextTick();
  expect(Repository.put).toHaveBeenCalledWith("/projects/12/notification-destination", {
    type: "webhook",
    enabled: true,
    url: "https://example.com/secret",
    token: "token-secret",
  });
  expect(wrapper.vm.url).toBe("");
  expect(wrapper.vm.token).toBe("");
});

test("stored token can be explicitly removed", async () => {
  await open();
  await wrapper.setData({ clearToken: true });
  await wrapper.vm.save();
  expect(Repository.put.mock.calls[0][1].token).toBe("");
});

test("authorization errors are displayed without closing the settings", async () => {
  await open();
  Repository.put.mockRejectedValue({
    response: { data: { message: "Only hub operators who administer this project can manage its notifications." } },
  });
  await wrapper.vm.save();
  expect(wrapper.vm.dialog).toBe(true);
  expect(wrapper.text()).toContain("Only hub operators");
});

test("removal only affects the selected project", async () => {
  await open();
  await wrapper.vm.remove();
  expect(Repository.delete).toHaveBeenCalledWith("/projects/12/notification-destination");
  expect(wrapper.vm.dialog).toBe(false);
});

test("invalid webhook URLs cannot be submitted", async () => {
  await open();
  await wrapper.setData({ url: "http://insecure.example.org" });
  await wrapper.vm.save();
  await flushPromises();
  expect(Repository.put).not.toHaveBeenCalled();
  expect(wrapper.vm.dialog).toBe(true);
  expect(wrapper.text()).toContain("Enter an HTTPS webhook URL");
});
afterEach(cleanupMounts);
