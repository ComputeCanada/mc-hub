import { mount } from "@vue/test-utils";
import { createAppVuetify } from "@/plugins/vuetify";
import ClusterResources from "@/components/cluster/ClusterResources";

test("renders current list slots and reports initial and in-place progress updates", async () => {
  const warn = jest.spyOn(console, "warn");
  const wrapper = mount(
    {
      components: { ClusterResources },
      data: () => ({
        progress: null,
        changes: [
          { address: "queued", type: "vm", change: { actions: ["create"], progress: "queued" } },
          { address: "running", type: "vm", change: { actions: ["update"], progress: "running" } },
          { address: "done", type: "vm", change: { actions: ["delete"], progress: "done" } },
          { address: "unchanged", type: "vm", change: { actions: ["no-op"] } },
        ],
      }),
      template: '<cluster-resources :resources-changes="changes" show-progress @update-progress="progress = $event"/>',
    },
    { global: { plugins: [createAppVuetify()] } }
  );
  try {
    expect(wrapper.vm.progress).toBe(50);
    expect(wrapper.findAll(".v-list-item-subtitle").map((node) => node.text())).toEqual(["done", "running", "queued"]);
    wrapper.vm.changes[0].change.progress = "done";
    await wrapper.vm.$nextTick();
    expect(wrapper.vm.progress).toBeCloseTo(83.333);
    await wrapper.setData({ changes: [] });
    expect(wrapper.vm.progress).toBe(0);
    expect(wrapper.text()).toContain("No resource to change");
    expect(warn).not.toHaveBeenCalled();
  } finally {
    wrapper.unmount();
    warn.mockRestore();
  }
});
