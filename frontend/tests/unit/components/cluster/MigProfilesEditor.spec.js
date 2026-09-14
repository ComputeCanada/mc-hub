import { mount } from "@vue/test-utils";
import Vue from "vue";
import Vuetify from "vuetify";
import MigProfilesEditor, { DEFAULT_MIG_PROFILES } from "@/components/cluster/MigProfilesEditor";
Vue.use(Vuetify);
const editor = (value = {}, additionalProfiles = []) =>
  mount(MigProfilesEditor, {
    vuetify: new Vuetify(),
    propsData: { value, additionalProfiles },
  });
const button = (wrapper, label) => wrapper.find(`[aria-label="${label}"]`);
const quantities = (wrapper) => wrapper.findAllComponents({ name: "v-text-field" });

describe("MIG profile rows", () => {
  it("starts empty, combines suggestions and accepts a custom profile", async () => {
    const wrapper = editor({}, ["1g.20gb", "1g.5gb"]);
    expect(wrapper.emitted("input")).toBeUndefined();
    await wrapper.findAllComponents({ name: "v-btn" }).at(0).trigger("click");
    const profile = wrapper.findComponent({ name: "v-combobox" });
    expect(profile.props("items")).toEqual([...DEFAULT_MIG_PROFILES, "1g.20gb"]);
    profile.vm.$emit("input", "2g.custom");
    await Vue.nextTick();
    expect(wrapper.emitted("input").slice(-1)[0]).toEqual([{ "2g.custom": 1 }]);
    wrapper.destroy();
  });

  it("counts weighted slices and disables increases and additions at seven", async () => {
    const wrapper = editor({ "1g.5gb": 2, "2g.10gb": 1, "3g.20gb": 1 });
    expect(wrapper.text()).toContain("7 / 7 used");
    expect(button(wrapper, "Increase quantity for profile 1").attributes("disabled")).toBe("disabled");
    expect(
      wrapper
        .findAllComponents({ name: "v-btn" })
        .wrappers.find((w) => w.text() === "Add profile")
        .props("disabled")
    ).toBe(true);
    await button(wrapper, "Decrease quantity for profile 1").trigger("click");
    expect(wrapper.emitted("input").slice(-1)[0]).toEqual([{ "1g.5gb": 1, "2g.10gb": 1, "3g.20gb": 1 }]);
    expect(button(wrapper, "Increase quantity for profile 1").attributes("disabled")).toBeUndefined();
    expect(button(wrapper, "Increase quantity for profile 2").attributes("disabled")).toBe("disabled");
    wrapper.destroy();
  });

  it.each(["0", "-1", "1.5", "8", ""])("rejects an invalid quantity %s", async (count) => {
    const wrapper = editor({ "1g.5gb": 1 });
    quantities(wrapper).at(0).vm.$emit("input", count);
    await Vue.nextTick();
    expect(wrapper.emitted("input")).toBeUndefined();
    expect(wrapper.emitted("invalid").slice(-1)[0]).toEqual([true]);
    const validation = wrapper.findAllComponents({ name: "v-input" }).wrappers.slice(-1)[0];
    expect(validation.vm.validate()).toBe(false);
    wrapper.destroy();
  });

  it("rejects duplicate and malformed custom names and clears the map on removal", async () => {
    const wrapper = editor({ "1g.5gb": 1, "2g.10gb": 1 });
    const profile = wrapper.findAllComponents({ name: "v-combobox" }).at(1);
    for (const name of ["1g.5gb", "custom", "8g.80gb"]) {
      profile.vm.$emit("input", name);
      await Vue.nextTick();
      expect(wrapper.emitted("input")).toBeUndefined();
      expect(wrapper.emitted("invalid").slice(-1)[0]).toEqual([true]);
    }
    await button(wrapper, "Remove profile 2").trigger("click");
    await button(wrapper, "Remove profile 1").trigger("click");
    expect(wrapper.emitted("input").slice(-1)[0]).toEqual([{}]);
    wrapper.destroy();
  });
});
