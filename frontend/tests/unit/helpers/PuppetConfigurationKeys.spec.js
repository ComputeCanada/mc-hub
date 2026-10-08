import axios from "axios";
import { getPuppetConfigurationKeys, parsePuppetConfigurationKeys } from "@/services/puppetConfigurationKeys";

jest.mock("axios");

const readme = `# Puppet Magic Castle
## \`profile::example\`
### parameters
| Variable | Description | Type |
| --- | --- | --- |
| \`setting\` | Setting | String |
| \`shares\` | Shares | Hash |

#### Nested fields
| Field | Description |
| \`path\` | Nested path |

### dependencies
| Variable | Description |
| \`ignored\` | Not a parameter |

## \`profile::second\`
### parameter
| Variable | Description |
| --- | --- |
| \`enabled\` | Enable it |
`;

beforeEach(() => axios.get.mockReset());

test("parses class parameters without suggesting nested fields or dependencies", () => {
  expect(parsePuppetConfigurationKeys(readme).map((parameter) => parameter.key)).toEqual([
    "profile::example::setting", "profile::example::shares", "profile::second::enabled",
  ]);
});

test("retains parameter descriptions and types when the parameters heading is missing", () => {
  const documentation = `## \`profile::software_stack\`
Configures the software environment.

| Variable | Description | Type |
| --- | --- | --- |
| \`initial_profile\` | Path to [initialization script](https://example.com) using \`bash\` | String |
| \`extra_site_env_vars\` | Environment variables | Hash[String, String] |

#### Nested fields
| Variable | Description | Type |
| \`ignored\` | Nested field | String |
`;
  expect(parsePuppetConfigurationKeys(documentation)).toEqual([
    { key: "profile::software_stack::extra_site_env_vars", description: "Environment variables", type: "Hash[String, String]", anchor: "profilesoftware_stack" },
    { key: "profile::software_stack::initial_profile", description: "Path to initialization script using bash", type: "String", anchor: "profilesoftware_stack" },
  ]);
  expect(parsePuppetConfigurationKeys(readme)).toContainEqual({
    key: "profile::second::enabled", description: "Enable it", type: "", anchor: "profilesecond",
  });
});

test("loads and caches each selected release separately", async () => {
  axios.get.mockResolvedValueOnce({ data: readme });
  const first = getPuppetConfigurationKeys("14.1.2");
  expect(getPuppetConfigurationKeys("14.1.2")).toBe(first);
  expect(await first).toContainEqual({
    key: "profile::example::setting", description: "Setting", type: "String",
    documentationUrl: "https://github.com/ComputeCanada/puppet-magic_castle/blob/14.1.2/README.md#profileexample",
  });
  expect(axios.get).toHaveBeenCalledWith(
    "https://raw.githubusercontent.com/ComputeCanada/puppet-magic_castle/14.1.2/README.md",
    { responseType: "text", timeout: 10000 }
  );
  axios.get.mockResolvedValueOnce({ data: readme.replace("setting", "new_setting") });
  expect(await getPuppetConfigurationKeys("15.0.0")).toEqual(expect.arrayContaining([expect.objectContaining({ key: "profile::example::new_setting" })]));
  expect(axios.get).toHaveBeenCalledTimes(2);
});

test("failed or unrecognized release documentation can be retried without a master fallback", async () => {
  axios.get.mockRejectedValueOnce(new Error("404"));
  await expect(getPuppetConfigurationKeys("missing")).rejects.toThrow("404");
  axios.get.mockResolvedValueOnce({ data: "Unknown README format" });
  await expect(getPuppetConfigurationKeys("missing")).rejects.toThrow("No Puppet configuration keys");
  axios.get.mockResolvedValueOnce({ data: readme });
  expect(await getPuppetConfigurationKeys("missing")).toEqual(expect.arrayContaining([expect.objectContaining({ key: "profile::example::setting" })]));
  expect(axios.get).toHaveBeenCalledTimes(3);
  expect(await getPuppetConfigurationKeys(null)).toEqual([]);
});
