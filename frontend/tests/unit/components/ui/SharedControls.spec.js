import { mount, flushPromises } from "@vue/test-utils";
import { createAppVuetify } from "@/plugins/vuetify";
import ConfirmDialog from "@/components/ui/ConfirmDialog";
import MessageDialog from "@/components/ui/MessageDialog";
import PublicKeyInput from "@/components/ui/PublicKeyInput";
import HieradataEditor from "@/components/ui/HieradataEditor";
import ResourceUsageDisplay from "@/components/ui/ResourceUsageDisplay";
import PasswordDisplay from "@/components/ui/PasswordDisplay";
import CopyButton from "@/components/ui/CopyButton";
import { getPuppetConfigurationKeys } from "@/services/puppetConfigurationKeys";

jest.mock("@/services/puppetConfigurationKeys");

let wrappers, hosts, warn;
beforeEach(() => {
  getPuppetConfigurationKeys.mockReset();
  getPuppetConfigurationKeys.mockResolvedValue(["profile::slurm::base::os_reserved_memory"]);
  wrappers = [];
  hosts = [];
  warn = jest.spyOn(console, "warn");
});
afterEach(() => {
  wrappers.forEach((wrapper) => wrapper.unmount());
  hosts.forEach((host) => host.remove());
  document.querySelectorAll(".v-overlay-container").forEach((node) => node.remove());
  expect(warn).not.toHaveBeenCalled();
  jest.restoreAllMocks();
});
function render(component, props = {}) {
  const host = document.createElement("div");
  document.body.append(host);
  hosts.push(host);
  // Deliberately use only production registration, not the all-components helper.
  const wrapper = mount(component, { props, attachTo: host, global: { plugins: [createAppVuetify()] } });
  wrappers.push(wrapper);
  return wrapper;
}
function button(text) {
  return [...document.querySelectorAll("button")].find((node) => node.textContent.trim() === text);
}

test.each([
  ["Yes", "confirm"],
  ["No", "cancel"],
])("confirmation %s closes the parent model and emits %s", async (label, event) => {
  const wrapper = render(ConfirmDialog, { modelValue: true });
  await flushPromises();
  button(label).click();
  await flushPromises();
  expect(wrapper.emitted(event)).toHaveLength(1);
  expect(wrapper.emitted("update:modelValue")).toEqual([[false]]);
  await wrapper.setProps({ modelValue: false });
  await wrapper.setProps({ modelValue: true });
  expect(wrapper.findComponent({ name: "VDialog" }).props("modelValue")).toBe(true);
});

test("message close invokes its callback and loading messages can stay persistent", async () => {
  const callback = jest.fn();
  const wrapper = render(MessageDialog, { modelValue: true, type: "success", callback });
  await flushPromises();
  button("Close").click();
  expect(callback).toHaveBeenCalledTimes(1);
  expect(wrapper.emitted("update:modelValue")).toEqual([[false]]);
  await wrapper.setProps({ type: "loading", persistent: true, noClose: true });
  expect(button("Close")).toBeUndefined();
  expect(wrapper.findComponent({ name: "VDialog" }).props("persistent")).toBe(true);
});

test("public keys update from pasted text, files and clearing", async () => {
  const wrapper = render(PublicKeyInput, { modelValue: [] });
  await wrapper.get("textarea").setValue("ssh-ed25519 first\n\nssh-rsa second\n");
  expect(wrapper.emitted("update:modelValue").pop()[0]).toEqual(["ssh-ed25519 first", "ssh-rsa second"]);
  // FileReader completes on its load event rather than a fixed sleep.
  const files = [new File(["ssh-ed25519 uploaded\n"], "id.pub")];
  const input = wrapper.get('input[type="file"]');
  Object.defineProperty(input.element, "files", { configurable: true, value: files });
  const loaded = new Promise((resolve) => {
    const read = FileReader.prototype.readAsText;
    jest.spyOn(FileReader.prototype, "readAsText").mockImplementation(function (file) {
      this.addEventListener("load", resolve);
      read.call(this, file);
    });
  });
  await input.trigger("change");
  await loaded;
  await flushPromises();
  expect(wrapper.emitted("update:modelValue").pop()[0]).toEqual(["ssh-ed25519 uploaded"]);
  await wrapper.findComponent({ name: "VFileInput" }).setValue([]);
  await flushPromises();
  expect(wrapper.emitted("update:modelValue").pop()[0]).toEqual([]);
});

test("hieradata edits preserve encrypted values and never mutate the supplied entries", async () => {
  const entries = [{ key: "secret", value: null, encrypt: true }];
  const wrapper = render(HieradataEditor, { modelValue: entries });
  await wrapper.get('input[type="text"]').setValue("renamed");
  expect(wrapper.emitted("update:modelValue").pop()[0]).toEqual([{ key: "renamed", value: null, encrypt: true }]);
  expect(entries).toEqual([{ key: "secret", value: null, encrypt: true }]);
  await wrapper.get('input[type="checkbox"]').setValue(false);
  expect(wrapper.emitted("update:modelValue").pop()[0]).toEqual([{ key: "renamed", value: "", encrypt: false }]);
  const fields = wrapper.findAll('input[type="text"]');
  await fields[1].setValue("plain");
  expect(wrapper.emitted("update:modelValue").pop()[0][0].value).toBe("plain");
});

test("hieradata keys filter README suggestions while accepting custom keys", async () => {
  const wrapper = render({
    components: { HieradataEditor },
    data: () => ({ entries: [{ key: "", value: "512", encrypt: false }] }),
    template: '<hieradata-editor v-model="entries" version="14.1.2"/>',
  });
  await flushPromises();
  const input = wrapper.get('input[role="combobox"]');
  await input.trigger("focus");
  await input.setValue("os_reserved_memory");
  await flushPromises();
  const options = [...document.querySelectorAll('[role="option"]')];
  expect(options.map((option) => option.textContent)).toEqual(["profile::slurm::base::os_reserved_memory"]);
  options[0].click();
  await flushPromises();
  expect(wrapper.vm.entries).toEqual([
    { key: "profile::slurm::base::os_reserved_memory", value: "512", encrypt: false },
  ]);
  await input.setValue("custom::module::setting");
  await input.trigger("blur");
  await flushPromises();
  expect(wrapper.vm.entries[0].key).toBe("custom::module::setting");
});

test("hieradata version changes discard stale suggestions and preserve entries", async () => {
  let resolveOldVersion;
  getPuppetConfigurationKeys.mockImplementationOnce(() => new Promise((resolve) => { resolveOldVersion = resolve; }));
  getPuppetConfigurationKeys.mockResolvedValueOnce(["profile::new::setting"]);
  const entries = [{ key: "custom::key", value: null, encrypt: true }];
  const wrapper = render(HieradataEditor, { version: "old", modelValue: entries });
  await wrapper.setProps({ version: "new" });
  await flushPromises();
  resolveOldVersion(["profile::old::setting"]);
  await flushPromises();
  expect(getPuppetConfigurationKeys).toHaveBeenLastCalledWith("new");
  expect(wrapper.findComponent({ name: "VCombobox" }).props("items")).toEqual(["profile::new::setting"]);
  expect(wrapper.vm.localEntries).toEqual(entries);
  expect(wrapper.emitted("update:modelValue")).toBeUndefined();

  getPuppetConfigurationKeys.mockRejectedValueOnce(new Error("Unavailable"));
  await wrapper.setProps({ version: "missing" });
  await flushPromises();
  expect(wrapper.findComponent({ name: "VCombobox" }).props("items")).toEqual([]);
  expect(wrapper.get('[role="status"]').text()).toContain("You can still enter a key");
  await wrapper.get('input[role="combobox"]').setValue("custom::replacement");
  expect(wrapper.emitted("update:modelValue").pop()[0][0].key).toBe("custom::replacement");
});

test("usage, password visibility and copy controls work with the production plugin", async () => {
  const usage = render(ResourceUsageDisplay, { used: 5, max: 10, title: "CPU" });
  expect(usage.get('[role="progressbar"]').attributes("aria-valuenow")).toBe("50");
  const password = render(PasswordDisplay, { password: "secret", color: "primary" });
  expect(password.text()).not.toContain("secret");
  await password.get("button").trigger("click");
  expect(password.text()).toContain("secret");
  const writeText = jest.fn().mockResolvedValue();
  Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText } });
  const copy = render(CopyButton, { text: "copied", color: "primary" });
  await copy.get("button").trigger("click");
  expect(writeText).toHaveBeenCalledWith("copied");
});

test("typing a second public key retains the newline through parent model updates", async () => {
  const wrapper = render({
    components: { PublicKeyInput },
    data: () => ({ keys: [] }),
    template: '<public-key-input v-model="keys"/>',
  });
  await wrapper.get("textarea").setValue("ssh-ed25519 first\n");
  expect(wrapper.get("textarea").element.value).toBe("ssh-ed25519 first\n");
  expect(wrapper.vm.keys).toEqual(["ssh-ed25519 first"]);
  await wrapper.get("textarea").setValue("ssh-ed25519 first\nssh-rsa second");
  expect(wrapper.vm.keys).toEqual(["ssh-ed25519 first", "ssh-rsa second"]);
  await wrapper.setData({ keys: ["ssh-rsa replacement"] });
  expect(wrapper.get("textarea").element.value).toBe("ssh-rsa replacement");
});
