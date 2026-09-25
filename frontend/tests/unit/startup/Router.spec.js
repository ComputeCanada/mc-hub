import { createMemoryHistory } from "vue-router";
import { createAppRouter } from "@/router";
import ProjectRepository from "@/repositories/ProjectRepository";

// Step 3 exercises production route definitions without compiling legacy screens.
jest.mock("@/views/Home", () => ({ render: () => null }));
jest.mock("@/views/CreateCluster", () => ({ render: () => null }));
jest.mock("@/views/Projects", () => ({ render: () => null }));
jest.mock("@/views/NotFound", () => ({ render: () => null }));
jest.mock("@/views/ModifyCluster", () => ({ render: () => null }));
jest.mock("@/views/CapacityPlanner", () => ({ render: () => null }));
jest.mock("@/views/Usage", () => ({ render: () => null }));
jest.mock("@/views/Benchmarks", () => ({ render: () => null }));
jest.mock("@/views/BenchmarkEditor", () => ({ render: () => null }));
jest.mock("@/repositories/ProjectRepository", () => ({ getAll: jest.fn() }));

beforeEach(() => {
  ProjectRepository.getAll.mockReset().mockResolvedValue({ data: [] });
});

test.each([
  ["/", "Home"],
  ["/capacity", "Capacity planner"],
  ["/usage", "Service adoption"],
  ["/projects", "Projects"],
  ["/create-cluster", "Create a Magic Castle"],
  ["/clusters/example.org", "Edit an existing Magic Castle"],
  ["/benchmarks", "Benchmarks"],
  ["/benchmarks/new", "New benchmark"],
  ["/benchmarks/example/edit", "Edit benchmark"],
  ["/unknown/nested/page", "Not Found"],
])("resolves %s to %s", (path, name) => {
  expect(createAppRouter(createMemoryHistory()).resolve(path).name).toBe(name);
});

test.each([
  ["", false, false],
  ["?showPlanConfirmation=1&destroy=1", true, true],
  ["?showPlanConfirmation=0&destroy=true", false, false],
])("preserves cluster route props for query %s", (query, showPlanConfirmation, destroy) => {
  const route = createAppRouter(createMemoryHistory()).resolve(`/clusters/example.org${query}`);
  expect(route.matched[0].props.default(route)).toEqual({ hostname: "example.org", showPlanConfirmation, destroy });
});

test("preserves benchmark ID props and the history base", () => {
  const router = createAppRouter(createMemoryHistory("/hub/"));
  const route = router.resolve("/benchmarks/example/edit");
  expect(route.params).toEqual({ id: "example" });
  expect(route.matched[0].props.default).toBe(true);
  expect(router.resolve("/projects").href).toBe("/hub/projects");
});

test.each(["/benchmarks", "/benchmarks/new", "/benchmarks/example/edit"])(
  "guards %s on every router instance",
  async (path) => {
    const denied = createAppRouter(createMemoryHistory());
    await denied.push(path);
    expect(denied.currentRoute.value.path).toBe("/");
    expect(denied.currentRoute.value.redirectedFrom.path).toBe(path);

    ProjectRepository.getAll.mockResolvedValue({ data: [{ admin: true }] });
    const allowed = createAppRouter(createMemoryHistory());
    await allowed.push(path);
    expect(allowed.currentRoute.value.path).toBe(path);
  }
);

test("ordinary routes do not invoke the permission guard's API request", async () => {
  const router = createAppRouter(createMemoryHistory());
  await router.push("/projects");
  expect(ProjectRepository.getAll).not.toHaveBeenCalled();
});
