import Repository from "./Repository";

const resource = "/projects";

export default {
  agentAvailability(id) {
    return Repository.get(`${resource}/${id}/agent-availability`, { timeout: 30000 });
  },
  openstackClouds() {
    return Repository.get(`${resource}/openstack/clouds`);
  },
  openstackSubnets(payload) {
    return Repository.post(`${resource}/openstack/subnets`, payload);
  },
  awsRegions(payload) {
    return Repository.post(`${resource}/aws/regions`, payload);
  },
  getAll() {
    return Repository.get(`${resource}`);
  },
  get(id) {
    return Repository.get(`${resource}/${id}`);
  },
  patch(id, payload) {
    return Repository.patch(`${resource}/${id}`, payload);
  },
  post(payload) {
    return Repository.post(`${resource}`, payload);
  },
  delete(id) {
    return Repository.delete(`${resource}/${id}`);
  },
};
