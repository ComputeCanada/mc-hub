import Vue from "vue";
import Vuetify from "vuetify";
import { shallowMount } from "@vue/test-utils";
import AWSCredentials from "@/components/ui/AWSCredentials";
import ProjectRepository from "@/repositories/ProjectRepository";

Vue.use(Vuetify);

jest.mock("@/repositories/ProjectRepository", () => ({ awsRegions: jest.fn() }));

describe("AWS credentials", () => {
  it("loads account-enabled regions and emits the selected region", async () => {
    ProjectRepository.awsRegions.mockResolvedValue({ data: { regions: ["ca-central-1"] } });
    const wrapper = shallowMount(AWSCredentials, {
      propsData: { value: { AWS_ACCESS_KEY_ID: "test", AWS_SECRET_ACCESS_KEY: "secret" } },
    });
    await wrapper.vm.loadRegions();
    expect(wrapper.vm.regions).toEqual(["ca-central-1"]);
    wrapper.vm.setRegion("ca-central-1");
    expect(wrapper.emitted("input").pop()[0].AWS_DEFAULT_REGION).toBe("ca-central-1");
    wrapper.destroy();
  });

  it("discards region discovery after credentials change", async () => {
    let resolve;
    ProjectRepository.awsRegions.mockReturnValue(
      new Promise((r) => {
        resolve = r;
      })
    );
    const wrapper = shallowMount(AWSCredentials, { propsData: { value: {} } });
    const request = wrapper.vm.loadRegions();
    await wrapper.setData({ secretKey: "different" });
    resolve({ data: { regions: ["us-east-1"] } });
    await request;
    expect(wrapper.vm.regions).toEqual([]);
    wrapper.destroy();
  });
});
