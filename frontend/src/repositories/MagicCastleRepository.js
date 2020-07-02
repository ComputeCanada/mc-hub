import Repository from "./Repository";

const resource = "/magic-castle";

export default {
  getAll() {
    return Repository.get(`${resource}`);
  },
  getState(hostname) {
    return Repository.get(`${resource}/${hostname}`);
  },
  getStatus(hostname) {
    return Repository.get(`${resource}/${hostname}/status`);
  },
  create(payload) {
    return Repository.post(`${resource}`, payload);
  },
  update(hostname, payload) {
    return Repository.put(`${resource}/${hostname}`, payload);
  },
  delete(hostname) {
    return Repository.delete(`${resource}/${hostname}`);
  },
  apply(hostname) {
    return Repository.post(`${resource}/${hostname}/apply`);
  }
};
