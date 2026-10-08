import axios from "axios";

const requests = new Map();

export function parsePuppetConfigurationKeys(readme) {
  const keys = new Map();
  // Only class parameter tables define top-level Hiera keys. Tables describing
  // nested hash fields and YAML examples must not become suggestions.
  for (const section of readme.split(/^## /m).slice(1)) {
    const className = section.match(/^`([^`]+)`/);
    const parameters = (section.split(/^### parameters?\s*$/m)[1] ?? section).split(/^#{2,6} /m)[0];
    if (!className || !parameters) continue;
    const table = parameters.match(/^\|\s*Variable[^\n]*\n((?:\|[^\n]*(?:\n|$))+)/m);
    if (!table) continue;
    for (const parameter of table[1].matchAll(/^\|\s*`([a-zA-Z0-9_]+)`\s*\|([^\n]*)/gm)) {
      const [description = "", type = ""] = parameter[2].split(/(?<!\\)\|/);
      const plainText = (value) => value.trim().replace(/\[([^\]]+)\]\([^)]*\)/g, "$1").replace(/`/g, "").replace(/\\\|/g, "|");
      const key = `${className[1]}::${parameter[1]}`;
      keys.set(key, {
        key,
        description: plainText(description),
        type: plainText(type),
        anchor: className[1].toLowerCase().replace(/[^\w-]/g, ""),
      });
    }
  }
  return [...keys.values()].sort((a, b) => a.key.localeCompare(b.key));
}

export function getPuppetConfigurationKeys(version) {
  if (!version) return Promise.resolve([]);
  if (!requests.has(version)) {
    // Magic Castle and puppet-magic_castle use synchronized release tags.
    const url = `https://raw.githubusercontent.com/ComputeCanada/puppet-magic_castle/${encodeURIComponent(version)}/README.md`;
    const request = axios.get(url, { responseType: "text", timeout: 10000 }).then(({ data }) => {
      const keys = parsePuppetConfigurationKeys(data);
      if (!keys.length) throw new Error("No Puppet configuration keys found in this release README.");
      return keys.map(({ anchor, ...parameter }) => ({
        ...parameter,
        documentationUrl: `https://github.com/ComputeCanada/puppet-magic_castle/blob/${encodeURIComponent(version)}/README.md#${anchor}`,
      }));
    }).catch((error) => {
      requests.delete(version);
      throw error;
    });
    requests.set(version, request);
  }
  return requests.get(version);
}
