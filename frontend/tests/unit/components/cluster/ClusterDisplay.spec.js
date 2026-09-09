import ClusterDisplay from "@/components/cluster/ClusterDisplay";
import ClusterStatusCode from "@/models/ClusterStatusCode";
import MagicCastleRepository from "@/repositories/MagicCastleRepository";
import { shallowMount } from "@vue/test-utils";

jest.mock("@/repositories/MagicCastleRepository", () => ({
  getStatus: jest.fn(),
  apply: jest.fn(),
  getState: jest.fn(),
}));

describe("ClusterDisplay", () => {
  const mountDisplay = () =>
    shallowMount(
      { ...ClusterDisplay, created() {} },
      {
        propsData: { hostname: "test.example.com" },
        data: () => ({
          status: ClusterStatusCode.CREATED,
          magicCastle: {},
          resourcesChanges: [{ address: "test", change: { actions: ["create"], progress: "queued" } }],
        }),
        stubs: [
          "v-container",
          "v-card",
          "v-card-title",
          "v-card-text",
          "v-list",
          "v-list-item",
          "v-list-item-content",
          "v-list-item-subtitle",
          "v-list-item-title",
          "v-divider",
        ],
      }
    );

  it("keeps the accepted plan visible and polls through delayed apply statuses", async () => {
    jest.useFakeTimers();
    let acceptApply;
    MagicCastleRepository.apply.mockReturnValue(
      new Promise((resolve) => {
        acceptApply = resolve;
      })
    );
    MagicCastleRepository.getStatus.mockResolvedValue({ data: { status: ClusterStatusCode.PLAN_RUNNING } });
    MagicCastleRepository.getState.mockResolvedValue({ data: {} });
    const wrapper = mountDisplay();
    const applying = wrapper.vm.applyCluster();
    await wrapper.vm.$nextTick();
    expect(wrapper.findComponent({ name: "ClusterEditor" }).exists()).toBe(false);
    expect(wrapper.findComponent({ name: "ClusterResources" }).props("showProgress")).toBe(true);
    acceptApply({});
    await applying;

    for (const status of [ClusterStatusCode.PLAN_RUNNING, ClusterStatusCode.CREATED, ClusterStatusCode.BUILD_RUNNING]) {
      MagicCastleRepository.getStatus.mockResolvedValue({ data: { status } });
      await wrapper.vm.fetchStatus();
      await wrapper.vm.$nextTick();
      expect(wrapper.vm.statusPoller).not.toBeNull();
      expect(wrapper.findComponent({ name: "ClusterEditor" }).exists()).toBe(false);
      expect(wrapper.vm.resourcesChanges).toHaveLength(1);
    }

    MagicCastleRepository.getStatus.mockResolvedValue({ data: { status: ClusterStatusCode.PROVISIONING_RUNNING } });
    await wrapper.vm.fetchStatus();
    expect(wrapper.vm.applyRequested).toBe(false);
    expect(wrapper.vm.statusPoller).toBeNull();
    expect(wrapper.vm.provisioningRunningDialog).toBe(true);
    wrapper.destroy();
    jest.useRealTimers();
  });

  it("ignores a status response that started before plan acceptance", async () => {
    let resolveStatus;
    MagicCastleRepository.getStatus.mockReturnValue(
      new Promise((resolve) => {
        resolveStatus = resolve;
      })
    );
    const wrapper = mountDisplay();
    const polling = wrapper.vm.fetchStatus();
    wrapper.vm.applyRequested = true;
    resolveStatus({ data: { status: ClusterStatusCode.CREATED, progress: [] } });
    await polling;
    expect(wrapper.vm.applyRequested).toBe(true);
    expect(wrapper.vm.resourcesChanges).toHaveLength(1);
    expect(wrapper.vm.statusPromise).toBeNull();
    wrapper.destroy();
  });

  it("shows completion when apply finishes between polls", async () => {
    MagicCastleRepository.getStatus.mockResolvedValue({
      data: { status: ClusterStatusCode.PROVISIONING_RUNNING },
    });
    MagicCastleRepository.getState.mockResolvedValue({ data: {} });
    const wrapper = mountDisplay();
    await wrapper.setData({ applyRequested: true, status: ClusterStatusCode.PLAN_RUNNING });
    await wrapper.vm.fetchStatus();
    expect(wrapper.vm.applyRequested).toBe(false);
    expect(wrapper.vm.provisioningRunningDialog).toBe(true);
    wrapper.destroy();
  });

  it("returns to the editor with an error when apply is rejected", async () => {
    MagicCastleRepository.apply.mockRejectedValue({ response: { data: { message: "Apply failed" } } });
    const wrapper = mountDisplay();
    await wrapper.vm.applyCluster();
    expect(wrapper.vm.applyRequested).toBe(false);
    expect(wrapper.vm.errorMessage).toBe("Apply failed");
    expect(wrapper.findComponent({ name: "ClusterEditor" }).exists()).toBe(true);
    wrapper.destroy();
  });

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

describe("retained cluster lifecycle", () => {
  it("requests teardown separately from permanent deletion", async () => {
    MagicCastleRepository.teardown = jest.fn().mockResolvedValue({});
    MagicCastleRepository.delete = jest.fn();
    const showPlanConfirmationDialog = jest.fn(async ({ planCreator, destroy }) => {
      expect(destroy).toBe(true);
      await planCreator();
    });
    await ClusterDisplay.methods.planDestruction.call({ hostname: "retained.example", showPlanConfirmationDialog });
    expect(MagicCastleRepository.teardown).toHaveBeenCalledWith("retained.example");
    expect(MagicCastleRepository.delete).not.toHaveBeenCalled();
  });

  it("saves undeployed configuration without applying a plan", async () => {
    MagicCastleRepository.update = jest.fn().mockResolvedValue({});
    const context = {
      hostname: "retained.example",
      magicCastle: { undeployed: true },
      $disableUnloadConfirmation: jest.fn(),
      startStatusPolling: jest.fn(),
      showPlanConfirmationDialog: jest.fn(),
    };
    await ClusterDisplay.methods.planModification.call(context);
    expect(MagicCastleRepository.update).toHaveBeenCalledWith(context.hostname, context.magicCastle);
    expect(context.showPlanConfirmationDialog).not.toHaveBeenCalled();
    expect(context.startStatusPolling).toHaveBeenCalled();
  });

  it("finishes polling when teardown has no resources", async () => {
    MagicCastleRepository.getStatus.mockResolvedValue({ data: { status: "not_deployed" } });
    const result = await ClusterDisplay.methods.waitForPlanCompletion.call({}, "empty.example");
    expect(result.status).toBe("not_deployed");
  });
});
