export const GPU_TYPE_PREFIX = "g";

export const isGpuTypeName = (name) => typeof name === "string" && name.startsWith(GPU_TYPE_PREFIX);

export function gpuCount(type) {
  if (typeof type?.gpus === "number") return type.gpus;
  if (type?.gpus?.length) {
    return type.gpus.reduce((total, gpu) => total + (gpu.count || 0) * (gpu.partition_size || 1), 0);
  }
  const match =
    type?.name?.match(/^g([0-9]+)(?:-[0-9.]+gb)?-/) || type?.name?.match(/^gpu.*-[a-zA-Z][a-zA-Z0-9]*x([0-9]+)$/);
  return match ? Number(match[1]) : 0;
}
