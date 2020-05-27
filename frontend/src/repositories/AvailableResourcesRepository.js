import Repository from "./Repository";

const resource = "/available-resources";

export default {
  get(clusterName = null) {
    if (clusterName) {
      return Repository.get(`${resource}/${clusterName}`);
    } else {
      return Repository.get(`${resource}`);
    }
  }
};
