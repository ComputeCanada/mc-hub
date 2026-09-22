import Vue from "vue";
import ProjectRepository from "@/repositories/ProjectRepository";

export const benchmarkAccess = Vue.observable({ allowed: false });
let pending = null;

export function refreshBenchmarkAccess() {
  if (!pending) {
    pending = ProjectRepository.getAll()
      .then(({ data }) => {
        benchmarkAccess.allowed = data.some((project) => project.admin === true);
        return benchmarkAccess.allowed;
      })
      .catch(() => {
        benchmarkAccess.allowed = false;
        return false;
      })
      .finally(() => {
        pending = null;
      });
  }
  return pending;
}

export async function guardBenchmarkAccess(to, from, next) {
  if (!to.matched.some((route) => route.meta.requiresProjectAdmin)) return next();
  if (await refreshBenchmarkAccess()) return next();
  next({ path: "/", replace: true });
}
