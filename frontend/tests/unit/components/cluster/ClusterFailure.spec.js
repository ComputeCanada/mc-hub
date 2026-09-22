import { shallowMount } from "@vue/test-utils";
import ClusterFailure from "@/components/cluster/ClusterFailure";

const mountFailure = (props = {}) =>
  shallowMount(ClusterFailure, {
    propsData: { hostname: "cluster.example", status: "build_error", ...props },
    stubs: ["v-alert", "v-btn"],
  });

describe("ClusterFailure", () => {
  it("shows diagnostics as text and recommends retry only for timeouts", () => {
    const wrapper = mountFailure({
      failure: { diagnostic: "Error: <script>bad</script>\ntimeout - SSH failed", timeout: true },
    });
    expect(wrapper.text()).toContain("Some changes may already have completed");
    expect(wrapper.text()).toContain("Review a new plan");
    expect(wrapper.find("script").exists()).toBe(false);
    wrapper.find("v-btn-stub").vm.$emit("click");
    expect(wrapper.emitted("retry")).toHaveLength(1);
    wrapper.destroy();
  });

  it("does not recommend retry for other failures or previous attempts", () => {
    const generic = mountFailure({ failure: { diagnostic: "Error: unexpected state ACTIVE", timeout: false } });
    expect(generic.text()).not.toContain("Review a new plan");
    const previous = mountFailure({ previous: true, failure: { diagnostic: "Error: timeout", timeout: true } });
    expect(previous.text()).toContain("Previous attempt failed");
    expect(previous.text()).not.toContain("Review a new plan");
    generic.destroy();
    previous.destroy();
  });

  it("provides a fallback and copies the run reference with diagnostics", async () => {
    const writeText = jest.fn().mockResolvedValue();
    Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText } });
    const wrapper = mountFailure({ failure: { run_id: "run-123", diagnostic: "" } });
    expect(wrapper.text()).toContain("Terraform did not provide additional error details");
    await wrapper.vm.copy();
    expect(writeText).toHaveBeenCalledWith(expect.stringContaining("run-123"));
    expect(wrapper.text()).toContain("Details copied");
    wrapper.destroy();
  });
});
