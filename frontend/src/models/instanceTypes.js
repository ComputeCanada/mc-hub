export const GPU_TYPE_PREFIX = "g";

export const isGpuTypeName = (name) => typeof name === "string" && name.startsWith(GPU_TYPE_PREFIX);
