import { mount, flushPromises } from "@vue/test-utils";
import { createAppVuetify } from "@/plugins/vuetify";
import InstanceSettings from "@/components/cluster/InstanceSettings";
import TypeSelect from "@/components/cluster/TypeSelect";

let wrapper, host, warn;
beforeEach(() => {
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
function render(component) {
  wrapper = mount(component, { attachTo: host, global: { plugins: [createAppVuetify()] } });
  return wrapper;
}
function field(label, name = "VTextField") {
  return wrapper.findAllComponents({ name }).find((input) => input.props("label") === label);
}

test("named model updates the parent specification without mutating its previous instance", async () => {
  render({
    components: { InstanceSettings },
    data: () => ({ specs: { instances: { node: { count: 2, tags: ["node", "spot"] } } }, invalid: false }),
    template:
      '<v-form ref="form"><instance-settings v-model:instance="specs.instances.node" provider="aws" has-gpu @invalid="invalid = $event"/></v-form>',
  });
  const original = wrapper.vm.specs.instances.node;
  await field("Root disk size").get("input").setValue("100");
  expect(wrapper.vm.specs.instances.node.disk_size).toBe(100);
  expect(original).not.toHaveProperty("disk_size");
  await field("Root disk size").get("input").setValue("1.5");
  expect(wrapper.vm.invalid).toBe(true);
  expect((await wrapper.vm.$refs.form.validate()).valid).toBe(false);
  await field("Root disk size").get("input").setValue("");
  expect(wrapper.vm.specs.instances.node).not.toHaveProperty("disk_size");
  await field("Wait for fulfillment", "VSelect").setValue(false);
  expect(wrapper.vm.specs.instances.node.wait_for_fulfillment).toBe(false);
  await field("Block duration").get("input").setValue("0");
  expect(wrapper.vm.specs.instances.node.block_duration_minutes).toBe(0);
  await field("Slurm features", "VCombobox").setValue(["fast", "gpu"]);
  expect(wrapper.vm.specs.instances.node.features).toEqual(["fast", "gpu"]);
  await field("Slurm features", "VCombobox").setValue([]);
  expect(wrapper.vm.specs.instances.node).not.toHaveProperty("features");
  expect(wrapper.vm.invalid).toBe(false);
});

test("nested MIG edits validate the form, recover and remove the optional map", async () => {
  render({
    components: { InstanceSettings },
    data: () => ({ instance: { count: 1, mig: { "1g.5gb": 2 } }, invalid: false }),
    template:
      '<v-form ref="form"><instance-settings v-model:instance="instance" has-gpu @invalid="invalid = $event"/></v-form>',
  });
  await field("Quantity").get("input").setValue("8");
  expect(wrapper.vm.instance.mig).toEqual({ "1g.5gb": 2 });
  expect(wrapper.vm.invalid).toBe(true);
  expect((await wrapper.vm.$refs.form.validate()).valid).toBe(false);
  await field("Quantity").get("input").setValue("3");
  expect(wrapper.vm.instance.mig).toEqual({ "1g.5gb": 3 });
  expect(wrapper.vm.invalid).toBe(false);
  expect((await wrapper.vm.$refs.form.validate()).valid).toBe(true);
  await wrapper.get('[aria-label="Remove profile 1"]').trigger("click");
  expect(wrapper.vm.instance).not.toHaveProperty("mig");
});

test("type menu renders groups and selects an actual type into the parent model", async () => {
  render({
    components: { TypeSelect },
    data: () => ({
      type: "",
      types: [
        { name: "ha1-2gb", vcpus: 1, ram: 2048 },
        { name: "x4-8gb", vcpus: 4, ram: 8192 },
      ],
    }),
    template: '<type-select v-model="type" :types="types"/>',
  });
  await wrapper.get(".v-field").trigger("mousedown");
  await flushPromises();
  expect(document.body.textContent).toContain("High availability types");
  const options = [...document.querySelectorAll('[role="option"]')];
  expect(options).toHaveLength(2);
  options.find((item) => item.textContent.includes("x4-8gb")).click();
  await flushPromises();
  expect(wrapper.vm.type).toBe("x4-8gb");
  await wrapper.setData({ type: "ha1-2gb" });
  expect(wrapper.get(".v-select__selection").text()).toBe("ha1-2gb");
});

test("AWS type menu prevents unavailable selections and preserves descriptions", async () => {
  render({
    components: { TypeSelect },
    data: () => ({
      type: "",
      types: [
        { name: "unavailable", quota_pool: "G", vcpus: 4, ram: 8192, hourly_price_usd: "0.2", unavailable: true },
        { name: "available", quota_pool: "G", vcpus: 2, ram: 4096, hourly_price_usd: "0.1" },
      ],
    }),
    template: '<type-select v-model="type" :types="types"/>',
  });
  await wrapper.get(".v-field").trigger("mousedown");
  await flushPromises();
  const options = [...document.querySelectorAll('[role="option"]')];
  expect(options[0].textContent).toContain("$0.1/hour");
  const disabled = options.find((item) => item.textContent.includes("unavailable"));
  expect(disabled.classList.contains("v-list-item--disabled")).toBe(true);
  disabled.click();
  await flushPromises();
  expect(wrapper.vm.type).toBe("");
  options[0].click();
  await flushPromises();
  expect(wrapper.vm.type).toBe("available");
});
