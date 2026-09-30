import { reactive } from "vue";
import ProjectRepository from "@/repositories/ProjectRepository";

export const benchmarkAccess = reactive({ allowed: false });
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

export async function guardBenchmarkAccess(to) {
  if (!to.matched.some((route) => route.meta.requiresProjectAdmin)) return true;
  if (await refreshBenchmarkAccess()) return true;
  return { path: "/", replace: true };
}
