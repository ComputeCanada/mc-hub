import Repository from "./Repository";

const resource = "/projects";

export default {
  getAll() {
    return Repository.get(`${resource}`);
  },
  post(payload) {
    return Repository.get(`${resource}`, payload);
  },
};
