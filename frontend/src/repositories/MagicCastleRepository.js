import Repository from "./Repository";

const resource = "/magic-castle";

export default {
  getAll() {
    return Repository.get(`${resource}`);
  },
  getState(clusterName) {
    return Repository.get(`${resource}/${clusterName}`);
  },
  getStatus(clusterName) {
    return Repository.get(`${resource}/${clusterName}/status`);
  },
  create(payload) {
    return Repository.post(`${resource}`, payload);
  },
  update(clusterName, payload) {
    return Repository.put(`${resource}/${clusterName}`, payload);
  },
  delete(clusterName) {
    return Repository.delete(`${resource}/${clusterName}`);
  }
};
