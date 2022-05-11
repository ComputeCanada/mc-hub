import Vue from "vue";
import VueRouter from "vue-router";
import Home from "@/views/Home";
import CreateCluster from "@/views/CreateCluster";
import NotFound from "@/views/NotFound";
import ModifyCluster from "@/views/ModifyCluster";

Vue.use(VueRouter);

const routes = [
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
    path: "*",
    name: "Not Found",
    component: NotFound,
  },
];

const router = new VueRouter({
  mode: "history",
  base: process.env.BASE_URL,
  routes,
});

export default router;
