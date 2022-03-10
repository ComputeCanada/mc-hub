import Repository from "./Repository";

const resource = "/available-resources";

export default {
  getHost(hostname) {
    return Repository.get(`${resource}/host/${hostname}`);
  },
  getCloud(cloud_id) {
    return Repository.get(`${resource}/cloud/${cloud_id}`);
  }
};
