import { createRouter, createWebHistory } from "vue-router";
import { guardBenchmarkAccess } from "@/services/benchmarkAccess";
import Home from "@/views/Home";
import CreateCluster from "@/views/CreateCluster";
import Projects from "@/views/Projects";
import NotFound from "@/views/NotFound";
import ModifyCluster from "@/views/ModifyCluster";

const routes = [
  { path: "/capacity", name: "Capacity planner", component: () => import("@/views/CapacityPlanner") },
  {
    path: "/benchmarks",
    name: "Benchmarks",
    component: () => import("@/views/Benchmarks"),
    meta: { requiresProjectAdmin: true },
  },
  {
    path: "/benchmarks/new",
    name: "New benchmark",
    component: () => import("@/views/BenchmarkEditor"),
    meta: { requiresProjectAdmin: true },
  },
  {
    path: "/benchmarks/:id/edit",
    name: "Edit benchmark",
    meta: { requiresProjectAdmin: true },
    component: () => import("@/views/BenchmarkEditor"),
    props: true,
  },
  { path: "/usage", name: "Service adoption", component: () => import("@/views/Usage") },
  {
    path: "/",
    name: "Home",
    component: Home,
  },
  {
    path: "/create-cluster",
    name: "Create a Magic Castle",
    component: CreateCluster,
  },
  {
    path: "/clusters/:hostname",
    name: "Edit an existing Magic Castle",
    component: ModifyCluster,
    props: (route) => ({
      showPlanConfirmation: route.query.showPlanConfirmation === "1",
      destroy: route.query.destroy === "1",
      ...route.params,
    }),
  },
  {
    path: "/projects",
    name: "Projects",
    component: Projects,
  },
  {
    path: "/:pathMatch(.*)*",
    name: "Not Found",
    component: NotFound,
  },
];

export function createAppRouter(history = createWebHistory(process.env.BASE_URL)) {
  const router = createRouter({ history, routes });
  router.beforeEach(guardBenchmarkAccess);
  return router;
}
