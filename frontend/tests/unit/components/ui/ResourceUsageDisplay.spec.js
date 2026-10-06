import { shallowMountWithVuetify as shallowMount, cleanupMounts } from "../../../helpers/mount";
import ResourceUsageDisplay from "@/components/ui/ResourceUsageDisplay";

describe("ResourceUsageDisplay", () => {
  it("displays resource values with at most two decimal places", () => {
    const wrapper = shallowMount(ResourceUsageDisplay, {
      props: {
        used: 16.666666,
        max: 216.125,
        title: "RAM",
        suffix: "GB",
      },
      global: { renderStubDefaultSlot: true, stubs: ["v-progress-circular"] },
    });

    expect(wrapper.vm.formattedUsed).toBe(16.67);
    expect(wrapper.vm.formattedMax).toBe(216.13);
  });

  it("does not add trailing zeroes", () => {
    const wrapper = shallowMount(ResourceUsageDisplay, {
      props: {
        used: 16.5,
        max: 216,
        title: "RAM",
        suffix: "GB",
      },
      global: { renderStubDefaultSlot: true, stubs: ["v-progress-circular"] },
    });

    expect(wrapper.vm.formattedUsed).toBe(16.5);
    expect(wrapper.vm.formattedMax).toBe(216);
  });
});
afterEach(cleanupMounts);
