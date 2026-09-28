import { mount, flushPromises } from "@vue/test-utils";
import { createAppVuetify } from "@/plugins/vuetify";
import ClusterDisplay from "@/components/cluster/ClusterDisplay";
import Repository from "@/repositories/MagicCastleRepository";

jest.mock("@/repositories/MagicCastleRepository", () => ({
  apply: jest.fn(),
  discardTeardown: jest.fn(),
  getStatus: jest.fn(),
}));
let wrapper, host, warn;
beforeEach(() => {
  jest.clearAllMocks();
  Repository.apply.mockResolvedValue({});
  Repository.discardTeardown.mockResolvedValue({});
  Repository.getStatus.mockResolvedValue({ data: { status: "destroy_running" } });
  host = document.createElement("div");
  document.body.append(host);
  warn = jest.spyOn(console, "warn");
});
afterEach(() => {
  wrapper?.unmount();
  host.remove();
  document.querySelectorAll(".v-overlay-container").forEach((node) => node.remove());
  expect(warn).not.toHaveBeenCalled();
  jest.restoreAllMocks();
});

test.each(["Yes", "No"])("teardown %s invokes only its confirmed action with real dialogs", async (answer) => {
  const push = jest.fn().mockResolvedValue();
  wrapper = mount(
    { ...ClusterDisplay, created() {} },
    {
      attachTo: host,
      props: { hostname: "test.example.org" },
      data: () => ({
        clusterDestructionDialog: true,
        resourcesChanges: [{ address: "node", type: "vm", change: { actions: ["delete"] } }],
      }),
      global: { plugins: [createAppVuetify()], stubs: { ClusterEditor: true }, mocks: { $router: { push } } },
    }
  );
  await flushPromises();
  const dialog = document.querySelector('[role="dialog"]');
  expect(dialog.textContent).toContain("Teardown confirmation");
  expect(dialog.textContent).toContain("node");
  [...dialog.querySelectorAll("button")].find((button) => button.textContent.trim() === answer).click();
  await flushPromises();
  if (answer === "Yes") {
    expect(Repository.apply).toHaveBeenCalledWith("test.example.org");
    expect(Repository.discardTeardown).not.toHaveBeenCalled();
    expect(push).not.toHaveBeenCalled();
  } else {
    expect(Repository.apply).not.toHaveBeenCalled();
    expect(Repository.discardTeardown).toHaveBeenCalledWith("test.example.org");
    expect(push).toHaveBeenCalledWith("/");
  }
});
