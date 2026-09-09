import { shallowMount } from "@vue/test-utils";
import CloudProviderInput from "@/components/ui/CloudProviderInput";
import ProjectMembership from "@/components/ui/ProjectMembership";
import ProjectRepository from "@/repositories/ProjectRepository";

jest.mock("@/repositories/ProjectRepository", () => ({
  post: jest.fn().mockResolvedValue({}),
  patch: jest.fn().mockResolvedValue({}),
}));

const project = { provider: "aws", members: [], admins: [], region: "ca-central-1", github_template: "" };

describe("AWS project price settings", () => {
  beforeEach(() => jest.clearAllMocks());

  it("includes the price ceiling when creating a project", async () => {
    const wrapper = shallowMount(CloudProviderInput);
    await wrapper.setData({ newProject: { provider: "aws", name: "AWS", github_template: "", env: {} } });
    await wrapper.setData({ newProject: { ...wrapper.vm.newProject, max_instance_hourly_price: "0.25" } });
    await wrapper.vm.add();
    expect(ProjectRepository.post.mock.calls[0][0].max_instance_hourly_price).toBe("0.25");
  });

  it.each(["0.25", 0, null, ""])("saves or clears the ceiling %s without credentials", async (price) => {
    const wrapper = shallowMount(ProjectMembership, { propsData: { id: 1, admin: true } });
    await wrapper.setData({ project, maxInstanceHourlyPrice: price, awsEnv: { AWS_DEFAULT_REGION: project.region } });
    await wrapper.vm.save();
    const payload = ProjectRepository.patch.mock.calls[0][1];
    expect(payload.max_instance_hourly_price).toBe(price === "" ? null : price);
    expect(payload.env).toBeUndefined();
  });
});
