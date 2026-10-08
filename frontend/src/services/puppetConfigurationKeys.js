import axios from "axios";

const requests = new Map();

export function parsePuppetConfigurationKeys(readme) {
  const keys = new Set();
  // Only class parameter tables define top-level Hiera keys. Tables describing
  // nested hash fields and YAML examples must not become suggestions.
  for (const section of readme.split(/^## /m).slice(1)) {
    const className = section.match(/^`([^`]+)`/);
    const parameters = section.split(/^### parameters?\s*$/m)[1]?.split(/^#{2,3} /m)[0];
    if (!className || !parameters) continue;
    const table = parameters.match(/^\|\s*Variable[^\n]*\n((?:\|[^\n]*(?:\n|$))+)/m);
    if (!table) continue;
    for (const parameter of table[1].matchAll(/^\|\s*`([a-zA-Z0-9_]+)`\s*\|/gm)) {
      keys.add(`${className[1]}::${parameter[1]}`);
    }
  }
  return [...keys].sort();
}

export function getPuppetConfigurationKeys(version) {
  if (!version) return Promise.resolve([]);
  if (!requests.has(version)) {
    // Magic Castle and puppet-magic_castle use synchronized release tags.
    const url = `https://raw.githubusercontent.com/ComputeCanada/puppet-magic_castle/${encodeURIComponent(version)}/README.md`;
    const request = axios.get(url, { responseType: "text", timeout: 10000 }).then(({ data }) => {
      const keys = parsePuppetConfigurationKeys(data);
      if (!keys.length) throw new Error("No Puppet configuration keys found in this release README.");
      return keys;
    }).catch((error) => {
      requests.delete(version);
      throw error;
    });
    requests.set(version, request);
  }
  return requests.get(version);
}
