import { shallowMountWithVuetify as shallowMount, cleanupMounts } from "../../../helpers/mount";
import StatusChip from "@/components/ui/StatusChip";

describe("StatusChip", () => {
  it.each([
    [true, "Not deployed"],
    [false, "Plan created"],
  ])("labels a ready plan with undeployed=%s as %s", (undeployed, label) => {
    const wrapper = shallowMount(StatusChip, {
      props: { status: "created", undeployed },
      global: { renderStubDefaultSlot: true, stubs: ["v-chip"] },
    });
    expect(wrapper.text()).toBe(label);
    wrapper.unmount();
  });

  it("shows an amber degraded status for a provisioned cluster with a service outage", () => {
    const wrapper = shallowMount(StatusChip, {
      props: {
        status: "provisioning_success",
        health: "degraded",
      },
      global: { renderStubDefaultSlot: true, stubs: ["v-chip"] },
    });

    expect(wrapper.vm.formattedStatus).toEqual({
      text: "Degraded",
      color: "amber darken-2",
    });
  });

  it("keeps the healthy status when every service is available", () => {
    const wrapper = shallowMount(StatusChip, {
      props: {
        status: "provisioning_success",
        health: "healthy",
      },
      global: { renderStubDefaultSlot: true, stubs: ["v-chip"] },
    });

    expect(wrapper.vm.formattedStatus).toEqual({ text: "Healthy", color: "green" });
  });
});
afterEach(cleanupMounts);
