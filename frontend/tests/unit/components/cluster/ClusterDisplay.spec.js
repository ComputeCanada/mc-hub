import ClusterDisplay from "@/components/cluster/ClusterDisplay";
import ClusterStatusCode from "@/models/ClusterStatusCode";
import MagicCastleRepository from "@/repositories/MagicCastleRepository";
import { shallowMount } from "@vue/test-utils";

jest.mock("@/repositories/MagicCastleRepository", () => ({
  getStatus: jest.fn(),
}));

describe("ClusterDisplay", () => {
  it("renders completed, active, and pending setup steps", () => {
    const wrapper = shallowMount(
      { ...ClusterDisplay, created() {} },
      {
        data: () => ({ creationStep: "terraform_workspace", clusterPlanRunningDialog: true }),
        stubs: ["v-container", "v-card", "v-card-title", "v-card-text", "v-progress-circular", "v-icon"],
      }
    );

    const rows = wrapper.findAll('[aria-live="polite"] > div');
    const rowText = (index) => rows.at(index).text().replace(/\s+/g, " ");
    expect(rowText(0)).toContain("Create GitHub repository — Done");
    expect(rowText(1)).toContain("Create Terraform workspace — In progress");
    expect(rowText(2)).toContain("Add variable file — Pending");
    expect(rowText(3)).toContain("Generate resource plan — Pending");
    wrapper.destroy();
  });

  it("updates creation progress from each status poll until the plan is ready", async () => {
    const steps = ["github_repository", "terraform_workspace", "variable_file", "resource_plan"];
    MagicCastleRepository.getStatus.mockReset();
    MagicCastleRepository.getStatus.mockResolvedValueOnce({ data: { status: ClusterStatusCode.NOT_FOUND } });
    steps.forEach((creation_step) => {
      MagicCastleRepository.getStatus.mockResolvedValueOnce({
        data: { status: ClusterStatusCode.PLAN_RUNNING, creation_step },
      });
    });
    const completed = { status: ClusterStatusCode.CREATED, progress: [{ resource: "test" }] };
    MagicCastleRepository.getStatus.mockResolvedValueOnce({ data: completed });
    const observed = [];
    const context = {
      ...ClusterDisplay.data(),
      sleep: jest.fn(async () => {
        observed.push(context.creationStep);
      }),
    };

    const result = await ClusterDisplay.methods.waitForPlanCompletion.call(context, "test.example.com");

    expect(observed).toEqual([null, ...steps]);
    expect(result).toEqual(completed);
  });

  it("uses generic plan feedback when the server does not report a creation step", async () => {
    MagicCastleRepository.getStatus.mockReset();
    MagicCastleRepository.getStatus.mockResolvedValueOnce({ data: { status: ClusterStatusCode.PLAN_ERROR } });
    const context = { ...ClusterDisplay.data(), creationStep: "github_repository" };

    const result = await ClusterDisplay.methods.waitForPlanCompletion.call(context, "test.example.com");

    expect(context.creationStep).toBeNull();
    expect(ClusterDisplay.computed.creationStepIndex.call(context)).toBe(-1);
    expect(result.status).toBe(ClusterStatusCode.PLAN_ERROR);
  });

  it("returns home without reloading a successfully destroyed cluster", async () => {
    MagicCastleRepository.getStatus.mockResolvedValue({
      data: {
        status: ClusterStatusCode.DESTROY_SUCCESS,
        stateful: false,
      },
    });

    const context = {
      statusPromise: null,
      status: ClusterStatusCode.DESTROY_RUNNING,
      stateful: true,
      resourcesChanges: [],
      stopStatusPolling: jest.fn(),
      showStatusDialog: jest.fn(),
      goHome: jest.fn(),
      loadCluster: jest.fn(),
    };
    Object.defineProperty(context, "busy", {
      get() {
        return [
          ClusterStatusCode.DESTROY_RUNNING,
          ClusterStatusCode.BUILD_RUNNING,
          ClusterStatusCode.PLAN_RUNNING,
        ].includes(this.status);
      },
    });

    await ClusterDisplay.methods.fetchStatus.call(context);

    expect(context.stopStatusPolling).toHaveBeenCalled();
    expect(context.goHome).toHaveBeenCalled();
    expect(context.showStatusDialog).not.toHaveBeenCalled();
    expect(context.loadCluster).not.toHaveBeenCalled();
  });
});
