import ClusterDisplay from "@/components/cluster/ClusterDisplay";
import ClusterStatusCode from "@/models/ClusterStatusCode";
import MagicCastleRepository from "@/repositories/MagicCastleRepository";

jest.mock("@/repositories/MagicCastleRepository", () => ({
  getStatus: jest.fn(),
}));

describe("ClusterDisplay", () => {
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
