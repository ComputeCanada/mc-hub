import { createApp, h } from "vue";
import { createRouter, createMemoryHistory, isNavigationFailure, NavigationFailureType } from "vue-router";
import UnloadConfirmation from "@/plugins/UnloadConfirmation";

const mounts = [];
let originalBeforeUnload;

async function setup() {
  const component = { render: () => h("div") };
  const router = createRouter({
    history: createMemoryHistory(),
    routes: ["/", "/next", "/last"].map((path) => ({ path, component })),
  });
  const app = createApp(component);
  app.use(UnloadConfirmation, { router });
  app.use(router);
  await router.isReady();
  app.mount(document.createElement("div"));
  mounts.push(app);
  return { app, router, helpers: app.config.globalProperties };
}

beforeEach(() => {
  originalBeforeUnload = window.onbeforeunload;
  jest.spyOn(window, "confirm").mockReturnValue(false);
});

afterEach(() => {
  mounts.reverse().forEach((app) => app.unmount());
  mounts.length = 0;
  window.onbeforeunload = originalBeforeUnload;
  jest.restoreAllMocks();
});

test("clean and explicitly saved forms navigate without prompting", async () => {
  const { router, helpers } = await setup();
  await router.push("/next");
  helpers.$enableUnloadConfirmation();
  helpers.$disableUnloadConfirmation();
  await router.push("/last");
  expect(router.currentRoute.value.path).toBe("/last");
  expect(window.confirm).not.toHaveBeenCalled();
});

test("cancelling repeatedly retains protection until navigation succeeds", async () => {
  const { router, helpers } = await setup();
  helpers.$enableUnloadConfirmation();
  for (let attempt = 0; attempt < 2; attempt++) {
    const failure = await router.push("/next");
    expect(isNavigationFailure(failure, NavigationFailureType.aborted)).toBe(true);
    expect(router.currentRoute.value.path).toBe("/");
  }
  expect(window.confirm).toHaveBeenCalledTimes(2);
  window.confirm.mockReturnValue(true);
  await router.push("/next");
  await router.push("/last");
  expect(window.confirm).toHaveBeenCalledTimes(3);
  expect(router.currentRoute.value.path).toBe("/last");
});

test("duplicate navigation does not clear dirty state", async () => {
  const { router, helpers } = await setup();
  helpers.$enableUnloadConfirmation();
  expect(isNavigationFailure(await router.push("/"), NavigationFailureType.duplicated)).toBe(true);
  await router.push("/next");
  expect(window.confirm).toHaveBeenCalledTimes(1);
  expect(router.currentRoute.value.path).toBe("/");
});

test.each(["abort", "throw"])("a later guard's %s retains dirty state after confirmation", async (kind) => {
  const { router, helpers } = await setup();
  helpers.$enableUnloadConfirmation();
  window.confirm.mockReturnValue(true);
  router.onError(() => {});
  const remove = router.beforeEach(() => {
    if (kind === "throw") throw new Error("Navigation failed");
    return false;
  });
  if (kind === "throw") await expect(router.push("/next")).rejects.toThrow("Navigation failed");
  else expect(isNavigationFailure(await router.push("/next"))).toBe(true);
  remove();
  window.confirm.mockReturnValue(false);
  await router.push("/next");
  expect(window.confirm).toHaveBeenCalledTimes(2);
  expect(router.currentRoute.value.path).toBe("/");
});

test("refresh protection follows dirty state", async () => {
  const { helpers } = await setup();
  const event = () => ({ preventDefault: jest.fn(), returnValue: undefined });
  const clean = event();
  window.onbeforeunload(clean);
  expect(clean.preventDefault).not.toHaveBeenCalled();
  helpers.$enableUnloadConfirmation();
  const dirty = event();
  window.onbeforeunload(dirty);
  expect(dirty.preventDefault).toHaveBeenCalled();
  expect(dirty.returnValue).toContain("Your changes will be lost");
  helpers.$disableUnloadConfirmation();
  const saved = event();
  window.onbeforeunload(saved);
  expect(saved.preventDefault).not.toHaveBeenCalled();
});

test("application instances have independent dirty state", async () => {
  const first = await setup();
  first.helpers.$enableUnloadConfirmation();
  const second = await setup();
  await second.router.push("/next");
  expect(window.confirm).not.toHaveBeenCalled();
  await first.router.push("/next");
  expect(window.confirm).toHaveBeenCalledTimes(1);
  expect(first.router.currentRoute.value.path).toBe("/");
});

test("unmount removes guards and restores the previous browser handler", async () => {
  const previous = jest.fn();
  window.onbeforeunload = previous;
  const { app, router, helpers } = await setup();
  helpers.$enableUnloadConfirmation();
  app.unmount();
  mounts.pop();
  expect(window.onbeforeunload).toBe(previous);
  await router.push("/next");
  expect(window.confirm).not.toHaveBeenCalled();
});

test("unmount preserves the session-expiry handler installed by the repository", async () => {
  const { app } = await setup();
  const sessionExpired = jest.fn();
  window.onbeforeunload = sessionExpired;
  app.unmount();
  mounts.pop();
  expect(window.onbeforeunload).toBe(sessionExpired);
});
