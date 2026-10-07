import cloneDeep from "lodash/cloneDeep";
import { generatePassword, generatePetName } from "@/models/utils";

// Copy only creation inputs; lifecycle and scheduling metadata belong to the source.
export function duplicateConfiguration(source) {
  const fields = [
    "cloud",
    "domain",
    "image",
    "mc_version",
    "nb_users",
    "instances",
    "volumes",
    "public_keys",
    "availability_zone",
    "hieradata_entries",
  ];
  const draft = Object.fromEntries(fields.filter((key) => key in source).map((key) => [key, cloneDeep(source[key])]));
  const name = generatePetName();
  draft.cluster_name = name === source.cluster_name ? `${name}-copy` : name;
  draft.guest_passwd = generatePassword();
  draft.expiration_date = null;
  // Ciphertext uses the source cluster's key and cannot be reused by a new cluster.
  draft.hieradata_entries = (draft.hieradata_entries || []).map((entry) =>
    entry.encrypt ? { ...entry, value: "" } : entry
  );
  return draft;
}
