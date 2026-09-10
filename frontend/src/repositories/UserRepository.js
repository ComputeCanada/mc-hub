import Repository from "./Repository";

const resource = "/users";

export default {
  getCurrent() {
    return Repository.get(`${resource}/me`);
  },
  setDefaultProject(projectId) {
    return Repository.patch(`${resource}/me`, { default_project_id: projectId });
  },
};
