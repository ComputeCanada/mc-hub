import Repository from "./Repository";

const resource = "/projects";

export default {
  getAll() {
    return Repository.get(`${resource}`);
  },
  get(id) {
    return Repository.get(`${resource}/${id}`);
  },
  patch(id, payload) {
    return Repository.patch(`${resource}/${id}`, payload);
  },
  post(payload) {
    return Repository.post(`${resource}`, payload);
  },
  delete(id) {
    return Repository.delete(`${resource}/${id}`);
  },
};
