import { flushPromises } from "@vue/test-utils";
import {
  mountWithVuetify,
  shallowMountWithVuetify,
  createTestRouter,
  createTestHost,
  cleanupMounts,
} from "../../helpers/mount";

afterEach(cleanupMounts);

test("fresh Vuetify mounts retain caller plugins, mocks, components and stubs without sharing state", async () => {
  const component = {
    data: () => ({ name: "" }),
    template:
      '<div><v-text-field v-model="name" label="Name"/><p>{{ name }} {{ $extra }} {{ $message }}</p><child-widget/></div>',
  };
  const extra = {
    install: (app) => {
      app.config.globalProperties.$extra = "plugin";
    },
  };
  const options = {
    global: {
      plugins: [extra],
      mocks: { $message: "mock" },
      components: { ChildWidget: { template: "<span>original</span>" } },
      stubs: { ChildWidget: { template: "<span>replacement</span>" } },
    },
  };
  const first = mountWithVuetify(component, options);
  const second = mountWithVuetify(component, options);
  await first.get("input").setValue("Felix");
  expect(first.text()).toContain("Felix plugin mock");
  expect(first.text()).toContain("replacement");
  expect(second.get("input").element.value).toBe("");
  first.vm.$vuetify.theme.change("dark");
  expect(second.vm.$vuetify.theme.global.name).toBe("light");
  expect(options.global.plugins).toEqual([extra]);
});

test("default slot rendering is a per-mount choice", () => {
  const component = { template: "<v-card>Visible content</v-card>" };
  const visible = shallowMountWithVuetify(component, { global: { renderStubDefaultSlot: true } });
  const hidden = shallowMountWithVuetify(component);
  expect(visible.text()).toBe("Visible content");
  expect(hidden.text()).toBe("");
});

test("memory routing works with real links and attached hosts are removed by cleanup", async () => {
  const router = await createTestRouter([
    { path: "/", component: { template: "<p>Home</p>" } },
    { path: "/next", component: { template: "<p>Next page</p>" } },
  ]);
  const host = createTestHost();
  const wrapper = mountWithVuetify(
    { template: '<div><v-btn to="/next">Next</v-btn><router-view/></div>' },
    {
      attachTo: host,
      global: { plugins: [router] },
    }
  );
  await wrapper.get("a").trigger("click");
  await flushPromises();
  expect(wrapper.text()).toContain("Next page");
  cleanupMounts();
  expect(wrapper.exists()).toBe(false);
  expect(host.isConnected).toBe(false);
});
