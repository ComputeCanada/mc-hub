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
  getPuppetConfigurationKeys.mockResolvedValue([{ key: "profile::slurm::base::os_reserved_memory", description: "Memory reserved for the operating system", type: "Integer", documentationUrl: "https://github.com/ComputeCanada/puppet-magic_castle/blob/14.1.2/README.md#profileslurmbase" }]);
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
  const encryptionToggle = wrapper.get('button[aria-label="Encrypt value"]');
  expect(encryptionToggle.attributes("aria-pressed")).toBe("true");
  await encryptionToggle.trigger("click");
  expect(encryptionToggle.attributes("aria-pressed")).toBe("false");
  expect(wrapper.emitted("update:modelValue").pop()[0]).toEqual([{ key: "renamed", value: "", encrypt: false }]);
  const fields = wrapper.findAll('input[type="text"]');
  await fields[1].setValue("plain");
  expect(wrapper.emitted("update:modelValue").pop()[0][0].value).toBe("plain");
});

test("expanded values preserve multiline YAML and only apply confirmed edits", async () => {
  const original = "modules:\n  - gcc\n  - openmpi\n";
  const wrapper = render(HieradataEditor, { modelValue: [{ key: "custom::settings", value: original, encrypt: false }] });
  expect(wrapper.findAllComponents({ name: "VTextField" }).find((field) => field.props("label") === "Value").props("modelValue")).toBe('{"modules":["gcc","openmpi"]}');
  const expand = wrapper.get('button[aria-label="Expand value editor"]');
  await expand.trigger("click");
  await flushPromises();
  const editor = wrapper.findComponent({ name: "VTextarea" });
  expect(editor.props("modelValue")).toBe(original);
  await editor.get("textarea").setValue("discard me");
  button("Cancel").click();
  await flushPromises();
  expect(wrapper.emitted("update:modelValue")).toBeUndefined();
  await expand.trigger("click");
  await flushPromises();
  const updated = "modules:\n  - gcc\nsettings:\n  enabled: true\n";
  await wrapper.findComponent({ name: "VTextarea" }).get("textarea").setValue(updated);
  button("Apply").click();
  await flushPromises();
  expect(wrapper.emitted("update:modelValue").pop()[0]).toEqual([{ key: "custom::settings", value: updated, encrypt: false }]);
  expect(wrapper.findAllComponents({ name: "VTextField" }).find((field) => field.props("label") === "Value").props("modelValue")).toBe('{"modules":["gcc"],"settings":{"enabled":true}}');
  await expand.trigger("click");
  await flushPromises();
  expect(wrapper.findComponent({ name: "VTextarea" }).props("modelValue")).toBe(updated);
});

test("toggling encryption preserves the multiline JSON preview and underlying value", async () => {
  const value = "modules:\n  - gcc\n";
  const wrapper = render(HieradataEditor, { modelValue: [{ key: "custom::settings", value, encrypt: false }] });
  const field = wrapper.findAllComponents({ name: "VTextField" }).find((field) => field.props("label") === "Value");
  const toggle = wrapper.get('button[aria-label="Encrypt value"]');
  expect(field.props("modelValue")).toBe('{"modules":["gcc"]}');
  for (const encrypt of [true, false]) {
    await toggle.trigger("click");
    expect(field.props("modelValue")).toBe('{"modules":["gcc"]}');
    expect(wrapper.emitted("update:modelValue").pop()[0]).toEqual([{ key: "custom::settings", value, encrypt }]);
  }
});

test("multiline values with Puppet interpolation show valid JSON previews", async () => {
  const value = "metrics: %{lookup('terraform.tag_ip.mgmt.0')}:9090\n";
  const wrapper = render(HieradataEditor, { modelValue: [{ key: "custom::metrics", value, encrypt: false }] });
  const field = wrapper.findAllComponents({ name: "VTextField" }).find((item) => item.props("label") === "Value");
  expect(field.props("modelValue")).toBe(JSON.stringify(value));

  const quotedYaml = 'metrics: "%{lookup(\'terraform.tag_ip.mgmt.0\')}:9090"\n';
  await wrapper.setProps({ modelValue: [{ key: "custom::metrics", value: quotedYaml, encrypt: false }] });
  expect(field.props("modelValue")).toBe('{"metrics":"%{lookup(\'terraform.tag_ip.mgmt.0\')}:9090"}');
});

test("expanded YAML values cannot be applied until valid", async () => {
  const invalid = "metrics: %{lookup('terraform.tag_ip.mgmt.0')}:9090\n";
  const wrapper = render(HieradataEditor, { modelValue: [{ key: "custom::metrics", value: "metrics: 9090\n", encrypt: false }] });
  await wrapper.get('button[aria-label="Expand value editor"]').trigger("click");
  await flushPromises();
  const editor = wrapper.findComponent({ name: "VTextarea" });
  await editor.get("textarea").setValue(invalid);
  expect(wrapper.vm.valueEditorError).toContain("Enter valid YAML before applying");
  expect(document.querySelector('[role="alert"]').textContent).toContain("Enter valid YAML before applying");
  expect(button("Apply").disabled).toBe(true);
  wrapper.vm.applyValueEditor();
  expect(wrapper.emitted("update:modelValue")).toBeUndefined();

  const valid = 'metrics: "%{lookup(\'terraform.tag_ip.mgmt.0\')}:9090"\n';
  await editor.get("textarea").setValue(valid);
  expect(button("Apply").disabled).toBe(false);
  button("Apply").click();
  await flushPromises();
  expect(wrapper.emitted("update:modelValue").pop()[0][0].value).toBe(valid);
});

test("opening an existing valid flow mapping with Puppet interpolation permits Apply", async () => {
  const existingValue = "{metrics: '%{lookup(''terraform.tag_ip.mgmt.0'')}:9090'}";
  const wrapper = render(HieradataEditor, {
    modelValue: [{ key: "custom::metrics", value: existingValue, encrypt: false }],
  });
  await wrapper.get('button[aria-label="Expand value editor"]').trigger("click");
  await flushPromises();
  expect(wrapper.vm.valueDraft).toBe(existingValue);
  expect(wrapper.vm.valueEditorError).toBe("");
  expect(button("Apply").disabled).toBe(false);
});

test("cancelling an expanded encrypted replacement preserves its write-only value", async () => {
  const wrapper = render(HieradataEditor, { modelValue: [{ key: "secret", value: null, encrypt: true }] });
  await wrapper.get('button[aria-label="Expand value editor"]').trigger("click");
  await flushPromises();
  expect(wrapper.findComponent({ name: "VTextarea" }).props("modelValue")).toBe("");
  expect(button("Apply").disabled).toBe(true);
  await wrapper.findComponent({ name: "VTextarea" }).get("textarea").setValue("replacement\nsecret");
  button("Cancel").click();
  await flushPromises();
  expect(wrapper.vm.localEntries[0]).toEqual({ key: "secret", value: null, encrypt: true });
  expect(wrapper.emitted("update:modelValue")).toBeUndefined();
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
  expect(wrapper.text()).not.toContain("Memory reserved for the operating system");
  await wrapper.findComponent({ name: "VCombobox" }).trigger("mouseenter");
  await new Promise((resolve) => setTimeout(resolve, 250));
  await flushPromises();
  const tooltip = wrapper.findComponent({ name: "VTooltip" });
  expect(document.querySelector('[role="tooltip"]').classList.contains("v-overlay--active")).toBe(true);
  expect(document.querySelector('[role="tooltip"]').textContent).toContain("Memory reserved for the operating system");
  await input.setValue("custom::module::setting");
  await input.trigger("blur");
  await flushPromises();
  expect(wrapper.vm.entries[0].key).toBe("custom::module::setting");
  expect(wrapper.text()).not.toContain("Memory reserved for the operating system");
  expect(tooltip.props("disabled")).toBe(true);
  expect(document.querySelector('[role="tooltip"]').classList.contains("v-overlay--active")).toBe(false);
});

test("hieradata version changes discard stale suggestions and preserve entries", async () => {
  let resolveOldVersion;
  getPuppetConfigurationKeys.mockImplementationOnce(() => new Promise((resolve) => { resolveOldVersion = resolve; }));
  getPuppetConfigurationKeys.mockResolvedValueOnce([{ key: "profile::new::setting" }]);
  const entries = [{ key: "custom::key", value: null, encrypt: true }];
  const wrapper = render(HieradataEditor, { version: "old", modelValue: entries });
  await wrapper.setProps({ version: "new" });
  await flushPromises();
  resolveOldVersion([{ key: "profile::old::setting" }]);
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
