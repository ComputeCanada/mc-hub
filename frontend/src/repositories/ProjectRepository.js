import Repository from "./Repository";

const resource = "/projects";

export default {
  getAll() {
    return Repository.get(`${resource}`);
  },
  post(payload) {
    return Repository.post(`${resource}`, payload);
  },
  delete(id) {
    return Repository.delete(`${resource}/${id}`);
  },
};
