import Repository from "./Repository";

const resource = "/template";

export default {
  get(name) {
    return Repository.get(`${resource}/${name}`);
  },
};
