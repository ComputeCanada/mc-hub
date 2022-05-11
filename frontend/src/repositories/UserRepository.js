import Repository from "./Repository";

const resource = "/users";

export default {
  getCurrent() {
    return Repository.get(`${resource}/me`);
  },
};
