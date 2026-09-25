import { nextTick } from "vue";
import { mountWithVuetify as mount, cleanupMounts } from "../../../helpers/mount";
import InstanceSettings from "@/components/cluster/InstanceSettings";

const editor = (instance = {}, provider = "openstack") =>
  mount(InstanceSettings, {
    props: { instance: { count: 4, tags: ["node"], ...instance }, name: "node", provider, hasGpu: true },
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
    wrapper.unmount();
  });

  it("edits numeric overrides and removes cleared values to restore defaults", async () => {
    const wrapper = editor();
    const disk = wrapper.findAllComponents({ name: "v-text-field" }).find((w) => w.props("label") === "Root disk size");
    await disk.setValue("100");
    await nextTick();
    expect(wrapper.props("instance").disk_size).toBe(100);
    await disk.setValue("");
    await nextTick();
    expect(wrapper.props("instance")).not.toHaveProperty("disk_size");
    wrapper.unmount();
  });

  it("keeps invalid MIG input out of the configuration and reports errors", async () => {
    const wrapper = editor({ mig: { "1g.5gb": 2 } });
    const mig = wrapper.findComponent({ name: "MigProfilesEditor" });
    const quantity = mig.findComponent({ name: "v-text-field" });
    await quantity.setValue("-1");
    await nextTick();
    expect(wrapper.props("instance").mig).toEqual({ "1g.5gb": 2 });
    expect(wrapper.emitted("invalid").slice(-1)[0]).toEqual([true]);
    await quantity.setValue("3");
    await nextTick();
    expect(wrapper.props("instance").mig).toEqual({ "1g.5gb": 3 });
    expect(wrapper.emitted("invalid").slice(-1)[0]).toEqual([false]);
    wrapper.unmount();
  });

  it("shows spot settings only for the matching provider and tags, preserving false", async () => {
    const wrapper = editor({ tags: ["node", "spot"] }, "aws");
    const wait = wrapper
      .findAllComponents({ name: "v-select" })
      .find((w) => w.props("label") === "Wait for fulfillment");
    await wait.setValue(false);
    expect(wrapper.props("instance").wait_for_fulfillment).toBe(false);
    await wrapper.setProps({ provider: "openstack" });
    expect(wrapper.text()).not.toContain("Provider options");
    wrapper.unmount();
  });
});
afterEach(cleanupMounts);
