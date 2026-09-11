import Repository from "./Repository";

const resource = "/available-resources";

export default {
  checkHost(hostname, definition) {
    return Repository.post(`${resource}/host/${hostname}`, definition);
  },
  checkCloud(id, definition) {
    return Repository.post(`${resource}/cloud/${id}`, definition);
  },
  getHost(hostname) {
    return Repository.get(`${resource}/host/${hostname}`);
  },
  getCloud(cloud_id) {
    return Repository.get(`${resource}/cloud/${cloud_id}`);
  },
};
