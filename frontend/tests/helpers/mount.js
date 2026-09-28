import { mount, shallowMount } from "@vue/test-utils";
import { createMemoryHistory, createRouter } from "vue-router";
import * as components from "vuetify/components";
import { appComponents, createAppVuetify } from "@/plugins/vuetify";

const featureComponents = Object.fromEntries(Object.entries(components).filter(([name]) => !(name in appComponents)));
const wrappers = new Set();
const hosts = new Set();

function mountComponent(mountFn, component, options) {
  const { global = {}, ...rest } = options;
  const wrapper = mountFn(component, {
    ...rest,
    global: {
      ...global,
      // Feature components are registered here for isolated tests. Production
      // registration remains part of each feature's migration in steps 5–6.
      components: { ...featureComponents, ...global.components },
      plugins: [createAppVuetify(), ...(global.plugins || [])],
    },
  });
  wrappers.add(wrapper);
  return wrapper;
}

export function mountWithVuetify(component, options = {}) {
  return mountComponent(mount, component, options);
}

export function shallowMountWithVuetify(component, options = {}) {
  return mountComponent(shallowMount, component, options);
}

export async function createTestRouter(routes, initialPath = "/") {
  const router = createRouter({ history: createMemoryHistory(), routes });
  await router.push(initialPath);
  await router.isReady();
  return router;
}

// Use as attachTo when testing DOM focus or teleported menus/dialogs.
export function createTestHost() {
  const host = document.createElement("div");
  document.body.append(host);
  hosts.add(host);
  return host;
}

export function cleanupMounts() {
  for (const wrapper of wrappers) {
    if (wrapper.exists()) wrapper.unmount();
  }
  wrappers.clear();
  for (const host of hosts) host.remove();
  hosts.clear();
}
