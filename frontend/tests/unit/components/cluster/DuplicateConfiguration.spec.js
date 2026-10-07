import { duplicateConfiguration } from "@/models/duplicateConfiguration";
import HieradataEditor from "@/components/ui/HieradataEditor";

jest.mock("@/models/utils", () => ({
  generatePetName: () => "new-name",
  generatePassword: () => "fresh-password",
}));

it("copies independent creation inputs and resets identity, secrets, and lifecycle metadata", () => {
  const source = {
    cluster_name: "new-name",
    domain: "example.com",
    cloud: { id: 1 },
    instances: { node: { count: 2 } },
    volumes: { nfs: { home: { size: 20 } } },
    public_keys: ["source-key"],
    guest_passwd: "old-password",
    expiration_date: "2020-01-01",
    mc_version: "14.1.2",
    image: "image",
    nb_users: 10,
    availability_zone: "zone",
    hieradata: "old ciphertext",
    hieradata_entries: [
      { key: "secret", value: null, encrypt: true },
      { key: "plain", value: "copied", encrypt: false },
    ],
    hostname: "new-name.example.com",
    status: "not_deployed",
    undeployed: true,
    capacity_plan_id: 4,
    capacity_ends_at: "tomorrow",
    owner: "source-owner",
  };
  const draft = duplicateConfiguration(source);
  expect(draft).toMatchObject({
    cluster_name: "new-name-copy",
    domain: source.domain,
    cloud: source.cloud,
    public_keys: source.public_keys,
    guest_passwd: "fresh-password",
    expiration_date: null,
    mc_version: source.mc_version,
    image: source.image,
    nb_users: 10,
    availability_zone: "zone",
  });
  for (const key of [
    "hieradata",
    "hostname",
    "status",
    "undeployed",
    "capacity_plan_id",
    "capacity_ends_at",
    "owner",
  ]) {
    expect(draft).not.toHaveProperty(key);
  }
  expect(draft.hieradata_entries[0].value).toBe("");
  expect(draft.hieradata_entries[1].value).toBe("copied");
  draft.instances.node.count = 9;
  expect(source.instances.node.count).toBe(2);
  expect(source.hieradata_entries[0].value).toBeNull();
});

it("requires a replacement for encrypted values", () => {
  expect(HieradataEditor.methods.requiredValue("")).not.toBe(true);
  expect(HieradataEditor.methods.requiredValue(null)).not.toBe(true);
  expect(HieradataEditor.methods.requiredValue("replacement")).toBe(true);
});
