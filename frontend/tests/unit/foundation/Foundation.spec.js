import { mount, flushPromises } from "@vue/test-utils";
import { createMemoryHistory } from "vue-router";
import FoundationApp from "@/foundation/FoundationApp.vue";
import { createFoundationRouter } from "@/foundation/router";
import { createFoundationVuetify } from "@/foundation/vuetify";

describe("Vue 3 dependency foundation", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
  });

  it("renders real Vuetify controls, updates state, and navigates to a lazy route", async () => {
    const router = createFoundationRouter(createMemoryHistory());
    await router.push("/");
    await router.isReady();
    wrapper = mount(FoundationApp, {
      global: { plugins: [router, createFoundationVuetify()] },
    });

    await wrapper.get("input").setValue("Felix");
    expect(wrapper.get('[data-testid="greeting"]').text()).toBe("Hello, Felix!");
    await wrapper.get('[data-testid="increment"]').trigger("click");
    expect(wrapper.get('[data-testid="increment"]').text()).toBe("Clicked 1 times");

    await wrapper.get('a[href="/about"]').trigger("click");
    await flushPromises();
    expect(router.currentRoute.value.path).toBe("/about");
    expect(wrapper.text()).toContain("Router integration");
    expect(wrapper.find("input").exists()).toBe(false);
  });
});
