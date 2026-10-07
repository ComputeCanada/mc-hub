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
  expect(parsePuppetConfigurationKeys(readme)).toEqual([
    "profile::example::setting", "profile::example::shares", "profile::second::enabled",
  ]);
});

test("loads and caches each selected release separately", async () => {
  axios.get.mockResolvedValueOnce({ data: readme });
  const first = getPuppetConfigurationKeys("14.1.2");
  expect(getPuppetConfigurationKeys("14.1.2")).toBe(first);
  await first;
  expect(axios.get).toHaveBeenCalledWith(
    "https://raw.githubusercontent.com/ComputeCanada/puppet-magic_castle/14.1.2/README.md",
    { responseType: "text", timeout: 10000 }
  );
  axios.get.mockResolvedValueOnce({ data: readme.replace("setting", "new_setting") });
  expect(await getPuppetConfigurationKeys("15.0.0")).toContain("profile::example::new_setting");
  expect(axios.get).toHaveBeenCalledTimes(2);
});

test("failed or unrecognized release documentation can be retried without a master fallback", async () => {
  axios.get.mockRejectedValueOnce(new Error("404"));
  await expect(getPuppetConfigurationKeys("missing")).rejects.toThrow("404");
  axios.get.mockResolvedValueOnce({ data: "Unknown README format" });
  await expect(getPuppetConfigurationKeys("missing")).rejects.toThrow("No Puppet configuration keys");
  axios.get.mockResolvedValueOnce({ data: readme });
  expect(await getPuppetConfigurationKeys("missing")).toContain("profile::example::setting");
  expect(axios.get).toHaveBeenCalledTimes(3);
  expect(await getPuppetConfigurationKeys(null)).toEqual([]);
});
