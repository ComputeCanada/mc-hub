import { nextTick } from "vue";
import { mountWithVuetify as mount, cleanupMounts } from "../../../helpers/mount";
import MigProfilesEditor, { DEFAULT_MIG_PROFILES } from "@/components/cluster/MigProfilesEditor";
const editor = (value = {}, additionalProfiles = []) =>
  mount(MigProfilesEditor, {
    props: { value, additionalProfiles },
  });
const button = (wrapper, label) => wrapper.find(`[aria-label="${label}"]`);
const quantities = (wrapper) => wrapper.findAllComponents({ name: "v-text-field" });

describe("MIG profile rows", () => {
  it("starts empty, combines suggestions and accepts a custom profile", async () => {
    const wrapper = editor({}, ["1g.20gb", "1g.5gb"]);
    expect(wrapper.emitted("input")).toBeUndefined();
    await wrapper.findAllComponents({ name: "v-btn" })[0].trigger("click");
    const profile = wrapper.findComponent({ name: "v-combobox" });
    expect(profile.props("items")).toEqual([...DEFAULT_MIG_PROFILES, "1g.20gb"]);
    await profile.setValue("2g.custom");
    await nextTick();
    expect(wrapper.emitted("input").slice(-1)[0]).toEqual([{ "2g.custom": 1 }]);
    wrapper.unmount();
  });

  it("counts weighted slices and disables increases and additions at seven", async () => {
    const wrapper = editor({ "1g.5gb": 2, "2g.10gb": 1, "3g.20gb": 1 });
    expect(wrapper.text()).toContain("7 / 7 used");
    expect(button(wrapper, "Increase quantity for profile 1").element.disabled).toBe(true);
    expect(
      wrapper
        .findAllComponents({ name: "v-btn" })
        .find((w) => w.text() === "Add profile")
        .props("disabled")
    ).toBe(true);
    await button(wrapper, "Decrease quantity for profile 1").trigger("click");
    expect(wrapper.emitted("input").slice(-1)[0]).toEqual([{ "1g.5gb": 1, "2g.10gb": 1, "3g.20gb": 1 }]);
    expect(button(wrapper, "Increase quantity for profile 1").element.disabled).toBe(false);
    expect(button(wrapper, "Increase quantity for profile 2").element.disabled).toBe(true);
    wrapper.unmount();
  });

  it.each(["0", "-1", "1.5", "8", ""])("rejects an invalid quantity %s", async (count) => {
    const wrapper = editor({ "1g.5gb": 1 });
    await quantities(wrapper)[0].setValue(count);
    await nextTick();
    expect(wrapper.emitted("input")).toBeUndefined();
    expect(wrapper.emitted("invalid").slice(-1)[0]).toEqual([true]);
    const validation = wrapper.findAllComponents({ name: "v-input" }).slice(-1)[0];
    expect(await validation.vm.validate()).not.toHaveLength(0);
    wrapper.unmount();
  });

  it("rejects duplicate and malformed custom names and clears the map on removal", async () => {
    const wrapper = editor({ "1g.5gb": 1, "2g.10gb": 1 });
    const profile = wrapper.findAllComponents({ name: "v-combobox" })[1];
    for (const name of ["1g.5gb", "custom", "8g.80gb"]) {
      await profile.setValue(name);
      await nextTick();
      expect(wrapper.emitted("input")).toBeUndefined();
      expect(wrapper.emitted("invalid").slice(-1)[0]).toEqual([true]);
    }
    await button(wrapper, "Remove profile 2").trigger("click");
    await button(wrapper, "Remove profile 1").trigger("click");
    expect(wrapper.emitted("input").slice(-1)[0]).toEqual([{}]);
    wrapper.unmount();
  });
});
afterEach(cleanupMounts);
