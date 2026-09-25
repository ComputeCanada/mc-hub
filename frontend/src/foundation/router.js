import { createRouter } from "vue-router";
import FoundationHome from "@/foundation/FoundationHome.vue";

export function createFoundationRouter(history) {
  return createRouter({
    history,
    routes: [
      { path: "/", component: FoundationHome },
      { path: "/about", component: () => import("@/foundation/FoundationAbout.vue") },
    ],
  });
}
