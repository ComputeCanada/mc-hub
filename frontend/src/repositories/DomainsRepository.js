import Repository from "./Repository";

const resource = "/domains";

export default {
  getDomains() {
    return Repository.get(`${resource}/`);
  },
};
