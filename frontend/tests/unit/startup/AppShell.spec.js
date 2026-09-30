import { h } from "vue";
import { mount, flushPromises } from "@vue/test-utils";
import { createRouter, createMemoryHistory } from "vue-router";
import axios from "axios";
import App from "@/App.vue";
import { createAppVuetify } from "@/plugins/vuetify";
import UnloadConfirmation from "@/plugins/UnloadConfirmation";
import ProjectRepository from "@/repositories/ProjectRepository";
import UserRepository from "@/repositories/UserRepository";
import { benchmarkAccess } from "@/services/benchmarkAccess";

jest.mock("axios", () => ({ get: jest.fn() }));
jest.mock("@/repositories/ProjectRepository", () => ({ getAll: jest.fn() }));
jest.mock("@/repositories/UserRepository", () => ({ getCurrent: jest.fn() }));

let wrapper;
let host;
let warn;

async function setup() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: ["/", "/capacity", "/projects", "/benchmarks", "/usage"].map((path) => ({
      path,
      component: { render: () => h("p", `Page: ${path}`) },
    })),
  });
  await router.push("/");
  await router.isReady();
  host = document.createElement("div");
  host.id = "app";
  document.body.append(host);
  wrapper = mount(App, {
    attachTo: host,
    global: { plugins: [[UnloadConfirmation, { router }], createAppVuetify(), router] },
  });
  await flushPromises();
  return router;
}

async function openAccount() {
  await wrapper
    .findAll("button")
    .find((button) => button.text().includes("Felix"))
    .trigger("click");
  await flushPromises();
}

beforeEach(() => {
  benchmarkAccess.allowed = false;
  ProjectRepository.getAll.mockReset().mockResolvedValue({ data: [] });
  UserRepository.getCurrent.mockReset().mockResolvedValue({
    data: { username: "Felix", usertype: "saml", is_admin: true },
  });
  axios.get.mockReset().mockResolvedValue({ data: { providers: [] } });
  Object.defineProperty(document, "hidden", { configurable: true, value: false });
  warn = jest.spyOn(console, "warn");
});

afterEach(() => {
  wrapper?.unmount();
  host?.remove();
  document.querySelectorAll(".v-overlay-container").forEach((node) => node.remove());
  expect(warn).not.toHaveBeenCalled();
  jest.restoreAllMocks();
});

test("renders the real shell and updates benchmark navigation when permissions change", async () => {
  const router = await setup();
  async function clickRoute(path) {
    // VMenu's back-button guard can defer navigation to a later event-loop turn.
    const finished = new Promise((resolve) => {
      const remove = router.afterEach(() => {
        remove();
        resolve();
      });
    });
    await wrapper.get(`a[href="${path}"]`).trigger("click");
    await finished;
    await flushPromises();
  }
  expect(wrapper.get("main").text()).toContain("Page: /");
  expect(document.querySelectorAll("#app")).toHaveLength(1);
  expect(wrapper.find('a[href="/benchmarks"]').exists()).toBe(false);
  ProjectRepository.getAll.mockResolvedValue({ data: [{ admin: true }] });
  await clickRoute("/capacity");
  expect(router.currentRoute.value.path).toBe("/capacity");
  expect(wrapper.get('a[href="/benchmarks"]').text()).toBe("Benchmarks");
  ProjectRepository.getAll.mockResolvedValue({ data: [] });
  await clickRoute("/");
  expect(wrapper.find('a[href="/benchmarks"]').exists()).toBe(false);
});

test("opens the account menu, preserves actions, and protects Projects navigation", async () => {
  ProjectRepository.getAll.mockResolvedValue({ data: [{ admin: true }] });
  const router = await setup();
  await openAccount();
  const menu = document.querySelector(".v-overlay__content");
  expect(menu.querySelector('a[href="/capacity"]')).not.toBeNull();
  expect(menu.querySelector('a[href="/benchmarks"]')).not.toBeNull();
  expect(menu.querySelector('a[href="/usage"]')).not.toBeNull();
  expect(menu.querySelector('a[href="/Shibboleth.sso/Logout"]')).not.toBeNull();
  wrapper.vm.$enableUnloadConfirmation();
  const confirm = jest.spyOn(window, "confirm").mockReturnValue(false);
  menu.querySelector('a[href="/projects"]').click();
  await flushPromises();
  expect(confirm).toHaveBeenCalledTimes(1);
  expect(router.currentRoute.value.path).toBe("/");
});

test("hides privileged and SAML-only account actions for a local non-admin", async () => {
  UserRepository.getCurrent.mockResolvedValue({ data: { username: "Felix", usertype: "local", is_admin: false } });
  await setup();
  await openAccount();
  const menu = document.querySelector(".v-overlay__content");
  expect(menu.querySelector('a[href="/projects"]')).not.toBeNull();
  expect(menu.querySelector('a[href="/benchmarks"]')).toBeNull();
  expect(menu.querySelector('a[href="/usage"]')).toBeNull();
  expect(menu.querySelector('a[href="/Shibboleth.sso/Logout"]')).toBeNull();
});

test("renders and expands a real Vuetify service-status alert", async () => {
  axios.get.mockResolvedValue({
    data: {
      providers: [
        {
          provider: "github",
          name: "GitHub",
          reported_status: "disruption",
          freshness: "fresh",
          last_success_at: new Date().toISOString(),
          affected_components: ["Actions"],
          incidents: [],
          status_url: "https://www.githubstatus.com/",
        },
      ],
    },
  });
  await setup();
  expect(wrapper.get(".v-alert").text()).toContain("GitHub reports a service disruption");
  await wrapper.get('button[aria-controls="service-status-details"]').trigger("click");
  expect(wrapper.get("#service-status-details").text()).toContain("Affected components: Actions");
});
