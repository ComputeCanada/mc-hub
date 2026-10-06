import { flushPromises } from "@vue/test-utils";
import { createAppRouter } from "@/router";
import ProjectRepository from "@/repositories/ProjectRepository";
import UserRepository from "@/repositories/UserRepository";
import axios from "axios";

jest.mock("@/views/Home", () => ({ template: "<p>Home page</p>" }));
jest.mock("@/views/CreateCluster", () => ({ render: () => null }));
jest.mock("@/views/Projects", () => ({ render: () => null }));
jest.mock("@/views/NotFound", () => ({ render: () => null }));
jest.mock("@/views/ModifyCluster", () => ({ render: () => null }));
jest.mock("@/router", () => ({
  createAppRouter: jest.fn(() =>
    jest.requireActual("@/router").createAppRouter(require("vue-router").createMemoryHistory())
  ),
}));
jest.mock("@/repositories/ProjectRepository", () => ({ getAll: jest.fn() }));
jest.mock("@/repositories/UserRepository", () => ({ getCurrent: jest.fn() }));
jest.mock("axios", () => ({ get: jest.fn() }));

test("the real entry waits for initial routing, mounts once, and installs component helpers", async () => {
  ProjectRepository.getAll.mockResolvedValue({ data: [] });
  UserRepository.getCurrent.mockResolvedValue({ data: { username: null } });
  axios.get.mockResolvedValue({ data: { providers: [] } });
  const host = document.createElement("div");
  host.id = "app";
  document.body.append(host);
  const { app, ready } = require("@/main");
  try {
    expect(host.innerHTML).toBe("");
    const instance = await ready;
    await flushPromises();
    expect(host.textContent).toContain("Home page");
    expect(createAppRouter).toHaveBeenCalledTimes(1);
    expect(instance.$enableUnloadConfirmation).toEqual(expect.any(Function));
    expect(instance.$disableUnloadConfirmation).toEqual(expect.any(Function));
    expect(instance.$router.currentRoute.value.path).toBe("/");
  } finally {
    app.unmount();
    host.remove();
  }
});
