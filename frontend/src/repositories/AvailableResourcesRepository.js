import Repository from "./Repository";

const resource = "/available-resources";

export default {
  get(hostname = null) {
    if (hostname) {
      return Repository.get(`${resource}/host/${hostname}`);
    } else {
      return Repository.get(`${resource}`);
    }
  },
  getCloud(cloud_id = null) {
    if (cloud_id) {
      return Repository.get(`${resource}/cloud/${cloud_id}`);
    } else {
      return Repository.get(`${resource}`);
    }
  }
};
