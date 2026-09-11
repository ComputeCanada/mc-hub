import { shallowMount } from "@vue/test-utils";
import ResourceUsageDisplay from "@/components/ui/ResourceUsageDisplay";

describe("ResourceUsageDisplay", () => {
  it("displays resource values with at most two decimal places", () => {
    const wrapper = shallowMount(ResourceUsageDisplay, {
      stubs: ["v-progress-circular"],
      propsData: {
        used: 16.666666,
        max: 216.125,
        title: "RAM",
        suffix: "GB",
      },
    });

    expect(wrapper.vm.formattedUsed).toBe(16.67);
    expect(wrapper.vm.formattedMax).toBe(216.13);
  });

  it("does not add trailing zeroes", () => {
    const wrapper = shallowMount(ResourceUsageDisplay, {
      stubs: ["v-progress-circular"],
      propsData: {
        used: 16.5,
        max: 216,
        title: "RAM",
        suffix: "GB",
      },
    });

    expect(wrapper.vm.formattedUsed).toBe(16.5);
    expect(wrapper.vm.formattedMax).toBe(216);
  });
});
