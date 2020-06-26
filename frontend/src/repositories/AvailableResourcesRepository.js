import Repository from "./Repository";

const resource = "/available-resources";

export default {
  get(hostname = null) {
    if (hostname) {
      return Repository.get(`${resource}/${hostname}`);
    } else {
      return Repository.get(`${resource}`);
    }
  }
};
