import { mount } from "@vue/test-utils";
import Vue from "vue";
import Vuetify from "vuetify";
import InstanceSettings from "@/components/cluster/InstanceSettings";
Vue.use(Vuetify);

const editor = (instance = {}, provider = "openstack") =>
  mount(InstanceSettings, {
    vuetify: new Vuetify(),
    propsData: { instance: { count: 4, tags: ["node"], ...instance }, name: "node", provider, hasGpu: true },
  });

describe("InstanceSettings", () => {
  it("shows MIG only for GPU instances while keeping Slurm features available", async () => {
    const wrapper = editor({ mig: { "1g.5gb": 2 } });
    expect(wrapper.findComponent({ name: "MigProfilesEditor" }).exists()).toBe(true);
    await wrapper.setProps({ hasGpu: false });
    expect(wrapper.findComponent({ name: "MigProfilesEditor" }).exists()).toBe(false);
    expect(wrapper.text()).toContain("Slurm features");
    expect(wrapper.props("instance").mig).toEqual({ "1g.5gb": 2 });
    await wrapper.setProps({ hasGpu: true });
    expect(wrapper.findComponent({ name: "MigProfilesEditor" }).exists()).toBe(true);
    wrapper.destroy();
  });

  it("edits numeric overrides and removes cleared values to restore defaults", async () => {
    const wrapper = editor();
    const disk = wrapper
      .findAllComponents({ name: "v-text-field" })
      .wrappers.find((w) => w.props("label") === "Root disk size");
    disk.vm.$emit("input", "100");
    await Vue.nextTick();
    expect(wrapper.props("instance").disk_size).toBe(100);
    disk.vm.$emit("input", "");
    await Vue.nextTick();
    expect(wrapper.props("instance")).not.toHaveProperty("disk_size");
    wrapper.destroy();
  });

  it("keeps invalid MIG input out of the configuration and reports errors", async () => {
    const wrapper = editor({ mig: { "1g.5gb": 2 } });
    const mig = wrapper.findComponent({ name: "MigProfilesEditor" });
    const quantity = mig.findComponent({ name: "v-text-field" });
    quantity.vm.$emit("input", "-1");
    await Vue.nextTick();
    expect(wrapper.props("instance").mig).toEqual({ "1g.5gb": 2 });
    expect(wrapper.emitted("invalid").slice(-1)[0]).toEqual([true]);
    quantity.vm.$emit("input", "3");
    await Vue.nextTick();
    expect(wrapper.props("instance").mig).toEqual({ "1g.5gb": 3 });
    expect(wrapper.emitted("invalid").slice(-1)[0]).toEqual([false]);
    wrapper.destroy();
  });

  it("shows spot settings only for the matching provider and tags, preserving false", async () => {
    const wrapper = editor({ tags: ["node", "spot"] }, "aws");
    const wait = wrapper
      .findAllComponents({ name: "v-select" })
      .wrappers.find((w) => w.props("label") === "Wait for fulfillment");
    wait.vm.$emit("change", false);
    expect(wrapper.props("instance").wait_for_fulfillment).toBe(false);
    await wrapper.setProps({ provider: "openstack" });
    expect(wrapper.text()).not.toContain("Provider options");
    wrapper.destroy();
  });
});
