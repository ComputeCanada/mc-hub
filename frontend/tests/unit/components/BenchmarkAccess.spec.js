import ProjectRepository from "@/repositories/ProjectRepository";
import { benchmarkAccess, refreshBenchmarkAccess, guardBenchmarkAccess } from "@/services/benchmarkAccess";

jest.mock("@/repositories/ProjectRepository", () => ({ getAll: jest.fn() }));
const route = { matched: [{ meta: { requiresProjectAdmin: true } }] };

beforeEach(() => {
  ProjectRepository.getAll.mockReset();
  benchmarkAccess.allowed = false;
});

test.each([[], [{ admin: false }], [{ admin: false }, { admin: false }]].map((projects) => [projects]))(
  "users without an administered project cannot navigate to benchmarks: %j",
  async (projects) => {
    ProjectRepository.getAll.mockResolvedValue({ data: projects });
    await expect(guardBenchmarkAccess(route)).resolves.toEqual({ path: "/", replace: true });
    expect(benchmarkAccess.allowed).toBe(false);
  }
);

test("one administered project enables access, and revocation clears it", async () => {
  ProjectRepository.getAll.mockResolvedValue({ data: [{ admin: false }, { admin: true }] });
  await expect(guardBenchmarkAccess(route)).resolves.toBe(true);
  expect(benchmarkAccess.allowed).toBe(true);
  ProjectRepository.getAll.mockResolvedValue({ data: [{ admin: false }] });
  await refreshBenchmarkAccess();
  expect(benchmarkAccess.allowed).toBe(false);
});

test("permission failures deny access and allow a later retry", async () => {
  benchmarkAccess.allowed = true;
  ProjectRepository.getAll.mockRejectedValueOnce(new Error("Unavailable"));
  await expect(guardBenchmarkAccess(route)).resolves.toEqual({ path: "/", replace: true });
  expect(benchmarkAccess.allowed).toBe(false);
  ProjectRepository.getAll.mockResolvedValue({ data: [{ admin: true }] });
  await expect(refreshBenchmarkAccess()).resolves.toBe(true);
  expect(ProjectRepository.getAll).toHaveBeenCalledTimes(2);
});

test("ordinary routes do not require a project administrator role", async () => {
  await expect(guardBenchmarkAccess({ matched: [{ meta: {} }] })).resolves.toBe(true);
  expect(ProjectRepository.getAll).not.toHaveBeenCalled();
});

test("guard and shell refreshes share an in-flight request, then permit another refresh", async () => {
  let resolve;
  ProjectRepository.getAll.mockReturnValue(new Promise((done) => (resolve = done)));
  const navigation = guardBenchmarkAccess(route);
  const refresh = refreshBenchmarkAccess();
  expect(ProjectRepository.getAll).toHaveBeenCalledTimes(1);
  resolve({ data: [{ admin: true }] });
  await expect(navigation).resolves.toBe(true);
  await expect(refresh).resolves.toBe(true);
  ProjectRepository.getAll.mockResolvedValue({ data: [] });
  await expect(refreshBenchmarkAccess()).resolves.toBe(false);
  expect(ProjectRepository.getAll).toHaveBeenCalledTimes(2);
});
