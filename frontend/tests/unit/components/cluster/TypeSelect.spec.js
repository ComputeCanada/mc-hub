import TypeSelect from "@/components/cluster/TypeSelect";
import { shallowMount, createLocalVue } from "@vue/test-utils";
import UnloadConfirmation from "@/plugins/UnloadConfirmation";
import Vuetify from "vuetify";
import Vue from "vue";
import router from "@/router";

Vue.use(Vuetify);

const localVue = createLocalVue();
const vuetify = new Vuetify();
localVue.use(Vuetify);
localVue.use(UnloadConfirmation, { router });

describe("TypeSelect", () => {
    it("getTypeDescription", () => {
        const wrapper = shallowMount(TypeSelect, {
            localVue,
            router,
            vuetify,
            propsData: {
                value: "",
                types: []
            }
        })
        // Regular types
        expect(wrapper.vm.getTypeDescription({name: "p1-0.5gb", vcpus: 1, ram: 512})).toBe("1 vCPU, 0.5 GB RAM");
        expect(wrapper.vm.getTypeDescription({name: "c1-0.5gb", vcpus: 1, ram: 512})).toBe("1 vCPU, 0.5 GB RAM");
        expect(wrapper.vm.getTypeDescription({name: "c16-1gb", vcpus: 16, ram: 1024})).toBe("16 vCPU, 1 GB RAM");
        expect(wrapper.vm.getTypeDescription({name: "c128-100gb", vcpus: 128, ram: 102400})).toBe("128 vCPU, 100 GB RAM");
        expect(wrapper.vm.getTypeDescription({name: "c128-100.25gb-1", vcpus: 128, ram: 102656})).toBe("128 vCPU, 100.25 GB RAM, 1 GB ephemeral storage");
        expect(wrapper.vm.getTypeDescription({name: "c128-100.25gb-10.5", vcpus: 128, ram: 102656})).toBe("128 vCPU, 100.25 GB RAM, 10.5 GB ephemeral storage");
        expect(wrapper.vm.getTypeDescription({name: "c62-256gb-10-numa", vcpus: 62, ram: 262144})).toBe("62 vCPU, 256 GB RAM, 10 GB ephemeral storage");

        // GPU types
        expect(wrapper.vm.getTypeDescription({name: "g1-18gb-c4-22gb", vcpus: 4, ram: 22528})).toBe("1 vGPU (18 GB), 4 vCPU, 22 GB RAM");
        expect(wrapper.vm.getTypeDescription({name: "g1-c14-56gb-500", vcpus: 14, ram: 57344})).toBe("1 vGPU, 14 vCPU, 56 GB RAM, 500 GB ephemeral storage");
        expect(wrapper.vm.getTypeDescription({name: "g2-c24-112gb-500", vcpus: 24, ram: 114688})).toBe("2 vGPU, 24 vCPU, 112 GB RAM, 500 GB ephemeral storage");
        expect(wrapper.vm.getTypeDescription({name: "g16-p24-112gb-2010.9", vcpus: 24, ram: 114688})).toBe("16 vGPU, 24 vCPU, 112 GB RAM, 2010.9 GB ephemeral storage");
    });
});
