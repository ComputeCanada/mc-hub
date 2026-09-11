import { shallowMount } from "@vue/test-utils";
import StatusChip from "@/components/ui/StatusChip";

describe("StatusChip", () => {
  it.each([
    [true, "Not deployed"],
    [false, "Plan created"],
  ])("labels a ready plan with undeployed=%s as %s", (undeployed, label) => {
    const wrapper = shallowMount(StatusChip, {
      stubs: ["v-chip"],
      propsData: { status: "created", undeployed },
    });
    expect(wrapper.text()).toBe(label);
    wrapper.destroy();
  });

  it("shows an amber degraded status for a provisioned cluster with a service outage", () => {
    const wrapper = shallowMount(StatusChip, {
      stubs: ["v-chip"],
      propsData: {
        status: "provisioning_success",
        health: "degraded",
      },
    });

    expect(wrapper.vm.formattedStatus).toEqual({
      text: "Degraded",
      color: "amber darken-2",
    });
  });

  it("keeps the healthy status when every service is available", () => {
    const wrapper = shallowMount(StatusChip, {
      stubs: ["v-chip"],
      propsData: {
        status: "provisioning_success",
        health: "healthy",
      },
    });

    expect(wrapper.vm.formattedStatus).toEqual({ text: "Healthy", color: "green" });
  });
});
