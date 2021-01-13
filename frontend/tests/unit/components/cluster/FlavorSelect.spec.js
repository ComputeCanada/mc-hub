import FlavorSelect from "@/components/cluster/FlavorSelect";
import {shallowMount, createLocalVue} from "@vue/test-utils";
import UnloadConfirmation from "@/plugins/UnloadConfirmation";
import Vuetify from "vuetify";
import Vue from "vue";
import router from "@/router";

Vue.use(Vuetify);

const localVue = createLocalVue();
const vuetify = new Vuetify();
localVue.use(Vuetify);
localVue.use(UnloadConfirmation, { router });

describe("FlavorSelect", () => {
  it("getFlavorDescription", () => {
      const wrapper = shallowMount(FlavorSelect, {
          localVue,
          router,
          vuetify,
          propsData: {
              value: "",
              flavors: []
          }
      })
      // Regular flavors
      expect(wrapper.vm.getFlavorDescription("p1-0.5gb")).toBe("1 vCPU, 0.5 GB RAM");
      expect(wrapper.vm.getFlavorDescription("c1-0.5gb")).toBe("1 vCPU, 0.5 GB RAM");
      expect(wrapper.vm.getFlavorDescription("c16-1gb")).toBe("16 vCPU, 1 GB RAM");
      expect(wrapper.vm.getFlavorDescription("c128-100gb")).toBe("128 vCPU, 100 GB RAM");
      expect(wrapper.vm.getFlavorDescription("c128-100.25gb-1")).toBe("128 vCPU, 100.25 GB RAM, 1 GB ephemeral storage");
      expect(wrapper.vm.getFlavorDescription("c128-100.25gb-10.5")).toBe("128 vCPU, 100.25 GB RAM, 10.5 GB ephemeral storage");
      expect(wrapper.vm.getFlavorDescription("c62-256gb-10-numa")).toBe("62 vCPU, 256 GB RAM, 10 GB ephemeral storage");

      // GPU flavors
      expect(wrapper.vm.getFlavorDescription("g1-18gb-c4-22gb")).toBe("1 vGPU (18 GB), 4 vCPU, 22 GB RAM");
      expect(wrapper.vm.getFlavorDescription("g1-c14-56gb-500")).toBe("1 vGPU, 14 vCPU, 56 GB RAM, 500 GB ephemeral storage");
      expect(wrapper.vm.getFlavorDescription("g2-c24-112gb-500")).toBe("2 vGPU, 24 vCPU, 112 GB RAM, 500 GB ephemeral storage");
      expect(wrapper.vm.getFlavorDescription("g16-p24-112gb-2010.9")).toBe("16 vGPU, 24 vCPU, 112 GB RAM, 2010.9 GB ephemeral storage");
  });
});
