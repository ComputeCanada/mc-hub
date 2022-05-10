<template>
  <div>
    <v-form ref="form" v-model="validForm">
      <v-subheader>General configuration</v-subheader>
      <v-list class="pt-0">
        <v-list-item v-if="!existingCluster">
          <v-select
            v-model="localSpecs.cloud_id"
            :items="user.projects"
            label="Cloud project"
            @change="changeCloudProject"
          />
        </v-list-item>
        <v-list-item v-if="!existingCluster">
          <v-text-field
            v-model="localSpecs.cluster_name"
            label="Cluster name"
            :rules="[clusterNameRegexRule]"
            validate-on-blur
          />
        </v-list-item>
        <v-list-item v-if="!existingCluster">
          <v-select
            v-model="localSpecs.domain"
            :items="getPossibleValues('domain')"
            label="Domain"
            :rules="[domainRule]"
          />
        </v-list-item>
        <v-list-item>
          <v-select
            v-model="localSpecs.image"
            :items="getPossibleValues('image')"
            label="Image"
          />
        </v-list-item>
        <v-list-item>
          <v-menu
            :nudge-right="40"
            transition="scale-transition"
            offset-y
            min-width="auto"
          >
            <template v-slot:activator="{ on, attrs }">
              <v-text-field
                v-model="localSpecs.expiration_date"
                label="Expiration date"
                prepend-icon="mdi-calendar"
                readonly
                v-bind="attrs"
                v-on="on"
              ></v-text-field>
            </template>
            <v-date-picker
              v-model="localSpecs.expiration_date"
              @input="menu2 = false"
              :min="tomorrowDate"
            ></v-date-picker>
          </v-menu>
        </v-list-item>
      </v-list>
      <v-divider />

      <!-- Instances -->
      <v-list class="pt-0">
        <v-list-item>
          <v-col cols="12" sm="3">
            <resource-usage-display
              :max="instanceCountMax"
              :used="instanceCountUsed"
              title="Instances"
            />
          </v-col>
          <v-col cols="12" sm="3">
            <resource-usage-display
              :max="ramGbMax"
              :used="ramGbUsed"
              title="RAM"
              suffix="GB"
            />
          </v-col>
          <v-col cols="12" sm="3">
            <resource-usage-display
              :max="vcpuMax"
              :used="vcpuUsed"
              title="cores"
            />
          </v-col>
          <v-col cols="12" sm="3">
            <resource-usage-display
              :max="volumeCountMax"
              :used="volumeCountUsed"
              title="volumes"
            />
          </v-col>
        </v-list-item>
      </v-list>
      <v-list>
        <div :key="id" v-for="id in Object.keys(localSpecs.instances)">
          <v-list-item>
            <v-col cols="12" sm="2" class="pt-0">
              <v-text-field
                v-model.number="localSpecs.instances[id].count"
                label="count"
                min="0"
                type="number"
                append-outer-icon="mdi-close"
                :rules="[countRule]"
              />
            </v-col>
            <v-col cols="12" sm="2" class="pt-0">
              <v-text-field
                :value="id"
                label="hostname prefix"
                v-on:change="changeHostnamePrefix(id, $event)"
                :rules="[hostnamePrefixRule(id)]"
              />
            </v-col>
            <v-col cols="12" sm="3" class="pt-0">
              <type-select
                :types="getTypes(localSpecs.instances[id].tags)"
                v-model="localSpecs.instances[id].type"
                label="Type"
                :rules="[ramRule, coreRule]"
              />
            </v-col>
            <v-col cols="12" sm="4" class="pt-0">
              <v-combobox
                v-model="localSpecs.instances[id].tags"
                :items="TAGS"
                label="tags"
                :rules="[publicTagRule(id)]"
                multiple
              ></v-combobox>
            </v-col>
            <v-col cols="12" sm="1" class="pt-0">
              <v-btn @click="rmInstanceRow(id)" text icon small color="error">
                <v-icon> mdi-delete </v-icon>
              </v-btn>
            </v-col>
          </v-list-item>
        </div>
        <div class="text-center">
          <v-btn @click="addInstanceRow" color="primary" class="ma-2">
            Add instance row
          </v-btn>
        </div>
      </v-list>
      <v-divider />
      <!-- Volumes -->
      <v-list>
        <v-list-item>
          <v-spacer></v-spacer>
          <v-col cols="12" sm="3">
            <resource-usage-display
              :max="volumeSizeMax"
              :used="volumeSizeUsed"
              title="volume storage"
              suffix="GB"
            />
          </v-col>
          <v-col cols="12" sm="3">
            <resource-usage-display
              :max="volumeCountMax"
              :used="volumeCountUsed"
              title="volumes"
            />
          </v-col>
          <v-spacer></v-spacer>
        </v-list-item>
      </v-list>
      <v-list>
        <div :key="tag" v-for="tag in Object.keys(localSpecs.volumes)">
          <div :key="id" v-for="id in Object.keys(localSpecs.volumes[tag])">
            <v-list-item>
              <v-spacer></v-spacer>
              <v-col cols="12" sm="2" class="pt-0">
                <v-combobox
                  :items="Object.keys(localSpecs.volumes)"
                  :value="tag"
                  label="tag"
                ></v-combobox>
                <!-- <v-text-field :value="tag" label="tag" readonly /> -->
              </v-col>
              <v-col cols="12" sm="3" class="pt-0">
                <v-text-field
                  :value="id"
                  label="volume name"
                  v-on:change="changeVolumeName(id, $event)"
                  :rules="[volumeNameRule(id)]"
                />
              </v-col>
              <v-col cols="12" sm="2" class="pt-0">
                <v-text-field
                  v-model.number="localSpecs.volumes.nfs[id].size"
                  type="number"
                  label="size"
                  prefix="GB"
                  :rules="[
                    volumeCountRule,
                    volumeSizeRule,
                    greaterThanZeroRule,
                  ]"
                  min="0"
                  dir="rtl"
                  reverse
                />
              </v-col>
              <v-col cols="12" sm="1" class="pt-0">
                <v-btn @click="rmVolumeRow(id)" text icon small color="error">
                  <v-icon> mdi-delete </v-icon>
                </v-btn>
              </v-col>
              <v-spacer></v-spacer>
            </v-list-item>
          </div>
        </div>
        <div class="text-center">
          <v-btn @click="addVolumeRow" color="primary" class="ma-2">
            Add volume row
          </v-btn>
        </div>
        <v-divider />
      </v-list>

      <!-- Networking & security -->
      <v-subheader>Networking and security</v-subheader>
      <v-list>
        <v-list-item>
          <v-combobox
            v-model="localSpecs.public_keys"
            label="SSH Keys"
            multiple
            chips
            append-icon
            clearable
            deletable-chips
            :rules="[publicKeysRule]"
            hint="Paste a key then press enter. Only the comment section will be displayed."
          >
            <template v-slot:selection="data">
              <v-chip
                :key="JSON.stringify(data.item)"
                v-bind="data.attrs"
                @click:close="data.parent.selectItem(data.item)"
                close
                close-icon="mdi-delete"
              >
                {{
                  data.item.split(" ").length > 2
                    ? data.item.split(" ")[2]
                    : data.item.slice(0, 15) + "..." + data.item.slice(-5)
                }}
              </v-chip>
            </template>
          </v-combobox>
        </v-list-item>
        <v-list-item>
          <v-text-field
            v-model.number="localSpecs.nb_users"
            type="number"
            label="Number of guest users"
            min="0"
          />
        </v-list-item>
        <v-list-item>
          <v-text-field
            v-model="localSpecs.guest_passwd"
            label="Guest password"
            :rules="[passwordLengthRule]"
          />
          <v-tooltip bottom>
            <template #activator="{ on, attrs }">
              <v-btn
                icon
                v-bind="attrs"
                v-on="on"
                @click="generateGuestPassword()"
              >
                <v-icon>mdi-refresh</v-icon>
              </v-btn>
            </template>
            <span>Generate new password</span>
          </v-tooltip>
        </v-list-item>
        <v-list-group prepend-icon="mdi-script-text-outline">
          <template #activator>
            <v-list-item-content>
              <v-list-item-title
                >Additional puppet configuration (optional)</v-list-item-title
              >
            </v-list-item-content>
          </template>
          <v-list-item>
            <v-list-item-content>
              <span class="mb-4" style="line-height: 18pt"
                >Configuration variables are documented in
                <a
                  href="https://github.com/ComputeCanada/puppet-magic_castle/blob/master/README.md#puppet-magic-castle"
                  target="_blank"
                  >puppet-magic_castle</a
                >
                and
                <a
                  href="https://github.com/ComputeCanada/puppet-jupyterhub/blob/master/README.md#hieradata-configuration"
                  target="_blank"
                  >puppet-jupyterhub</a
                >.
              </span>

              <code-editor
                v-model="localSpecs.hieradata"
                language="yaml"
                placeholder='profile::base::admin_email: "me@example.org"
jupyterhub::enable_otp_auth: false'
              />
            </v-list-item-content>
          </v-list-item>
        </v-list-group>
      </v-list>

      <!-- Apply and cancel -->
      <div class="text-center">
        <p v-if="!validForm" class="error--text">
          Some form fields are invalid.
        </p>
        <v-btn
          @click="apply"
          color="primary"
          class="ma-2"
          :disabled="!applyButtonEnabled"
          large
          >Apply</v-btn
        >
        <v-btn
          to="/"
          class="ma-2"
          :disabled="loading"
          large
          outlined
          color="primary"
          >Cancel</v-btn
        >
      </div>
    </v-form>
  </div>
</template>

<script>
import { cloneDeep, isEqual } from "lodash";
import { generatePassword, generatePetName } from "@/models/utils";
import ClusterStatusCode from "@/models/ClusterStatusCode";
import ResourceUsageDisplay from "@/components/ui/ResourceUsageDisplay";
import TypeSelect from "./TypeSelect";
import CodeEditor from "@/components/ui/CodeEditor";
import AvailableResourcesRepository from "@/repositories/AvailableResourcesRepository";

const MB_PER_GB = 1024;
const MINIMUM_PASSWORD_LENGTH = 8;
const CLUSTER_NAME_REGEX = /^[a-z]([a-z0-9-]*[a-z0-9]+)?$/;
const SSH_PUBLIC_KEY_REGEX =
  /^(ssh-rsa AAAAB3NzaC1yc2|ecdsa-sha2-nistp256 AAAAE2VjZHNhLXNoYTItbmlzdHAyNT|ecdsa-sha2-nistp384 AAAAE2VjZHNhLXNoYTItbmlzdHAzODQAAAAIbmlzdHAzOD|ecdsa-sha2-nistp521 AAAAE2VjZHNhLXNoYTItbmlzdHA1MjEAAAAIbmlzdHA1Mj|ssh-ed25519 AAAAC3NzaC1lZDI1NTE5|ssh-dss AAAAB3NzaC1kc3)[0-9A-Za-z+/]+[=]{0,3}( .*)?$/;

export default {
  name: "ClusterEditor",
  components: {
    CodeEditor,
    TypeSelect,
    ResourceUsageDisplay,
  },
  props: {
    specs: {
      type: Object,
      required: true,
    },
    existingCluster: {
      type: Boolean,
      required: true,
    },
    currentStatus: {
      type: String,
    },
    user: {
      type: Object,
    },
  },
  data: function () {
    return {
      DEFAULT_VOLUMES: ["home", "project", "scratch"],
      VOLUME_STUB: { size: 50 },
      TAGS: ["mgmt", "puppet", "nfs", "login", "proxy", "public", "node"],
      validForm: true,
      initialSpecs: null,

      clusterNameRegexRule: (value) =>
        value.match(CLUSTER_NAME_REGEX) !== null ||
        "Must contain lowercase alphanumeric characters and start with a letter. It can also include dashes.",
      greaterThanZeroRule: (value) =>
        (typeof value === "number" && value > 0) || "Must be greater than zero",
      positiveNumberRule: (value) =>
        (typeof value === "number" && value >= 0) ||
        "Must be a positive number",
      passwordLengthRule: (value) =>
        value.length >= MINIMUM_PASSWORD_LENGTH ||
        `The password must be at least ${MINIMUM_PASSWORD_LENGTH} characters long`,
      nowDate: new Date().toISOString().slice(0, 10),
      tomorrowDate: new Date(new Date().getTime() + 24 * 60 * 60 * 1000)
        .toISOString()
        .slice(0, 10),
      loading: false,
      quotas: null,
      possibleResources: null,
      resourceDetails: null,
    };
  },
  watch: {
    possibleResources(possibleResources) {
      // We set default values for select boxes based on possible resources fetched from the API
      // Domain
      if (this.localSpecs.domain === null) {
        try {
          this.localSpecs.domain = possibleResources.domain[0];
          this.initialSpecs.domain = possibleResources.domain[0];
        } catch (err) {
          console.log("No domain available");
        }
      }

      // Image
      if (this.localSpecs.image === null) {
        try {
          this.localSpecs.image = possibleResources.image[0];
          this.initialSpecs.image = possibleResources.image[0];
        } catch (err) {
          console.log("No image available");
        }
      }

      // Instance type
      for (let key in this.localSpecs.instances) {
        if (this.localSpecs.instances[key].type === null) {
          try {
            const type = this.getTypes(this.localSpecs.instances[key].tags)[0];
            this.localSpecs.instances[key].type = type;
            if (key in this.initialSpecs.instances) {
              this.initialSpecs.instances[key].type = type;
            }
          } catch (err) {
            console.log("No instance type available for " + key);
            console.log(err);
          }
        }
      }
    },
    dirtyForm(dirty) {
      if (dirty) {
        this.$enableUnloadConfirmation();
      } else {
        this.$disableUnloadConfirmation();
      }
    },
  },
  async created() {
    if (!this.existingCluster) {
      this.localSpecs.cloud_id = this.user.projects[0];
      this.localSpecs.cluster_name = generatePetName();
      this.localSpecs.guest_passwd = generatePassword();
      this.localSpecs.public_keys = this.user.public_keys.filter((key) =>
        key.match(SSH_PUBLIC_KEY_REGEX)
      );
    }
    this.initialSpecs = cloneDeep(this.localSpecs);
    await this.loadCloudResources();
  },
  updated() {
    this.$refs.form.validate();
  },
  beforeDestroy() {
    this.$disableUnloadConfirmation();
  },
  computed: {
    localSpecs: {
      get() {
        return this.specs;
      },
      set(localSpecs) {
        this.$emit("input", localSpecs);
      },
    },
    hostname() {
      return this.localSpecs.cluster_name + "." + this.localSpecs.domain;
    },
    applyRunning() {
      return [
        ClusterStatusCode.DESTROY_RUNNING,
        ClusterStatusCode.BUILD_RUNNING,
      ].includes(this.currentStatus);
    },
    dirtyForm() {
      const keysToCheck = [
        "volumes",
        "nb_users",
        "domain",
        "cluster_name",
        "hieradata",
        "image",
        "public_keys",
        "guest_passwd",
        "instances",
        "expiration_date",
        "cloud_id",
      ];
      if (this.existingCluster) {
        if (this.initialSpecs === null) {
          return false;
        }
        return keysToCheck.some(
          (key) => !isEqual(this.initialSpecs[key], this.localSpecs[key])
        );
      }
      return true;
    },
    domainRule() {
      return (
        (this.possibleResources &&
          this.possibleResources.domain.includes(this.localSpecs.domain)) ||
        "Invalid domain provided"
      );
    },
    volumeCountRule() {
      return (
        this.volumeCountUsed <= this.volumeCountMax ||
        "Volume number quota exceeded"
      );
    },
    volumeSizeRule() {
      return (
        this.volumeSizeUsed <= this.volumeSizeMax ||
        "Volume size quota exceeded"
      );
    },
    instanceCountUsed() {
      return this.usedResourcesLoaded
        ? this.instances.reduce((acc, instance) => acc + instance.count, 0)
        : 0;
    },
    instanceCountMax() {
      return this.quotas ? this.quotas.instance_count.max : 0;
    },
    ipsCountMax() {
      return this.quotas ? this.quotas.ips.max : 0;
    },
    ramRule() {
      return this.ramGbUsed <= this.ramGbMax || "Ram quota exceeded";
    },
    coreRule() {
      return this.vcpuUsed <= this.vcpuMax || "Core quota exceeded";
    },
    ramGbUsed() {
      return this.usedResourcesLoaded
        ? this.instances.reduce(
            (acc, instance) =>
              acc +
              instance.count * this.getInstanceDetail(instance.type, "ram"),
            0
          ) / MB_PER_GB
        : 0;
    },
    ramGbMax() {
      return this.quotas ? this.quotas.ram.max / MB_PER_GB : 0;
    },
    vcpuUsed() {
      return this.usedResourcesLoaded
        ? this.instances.reduce(
            (acc, instance) =>
              acc +
              instance.count * this.getInstanceDetail(instance.type, "vcpus"),
            0
          )
        : 0;
    },
    vcpuMax() {
      return this.quotas ? this.quotas.vcpus.max : 0;
    },
    volumeCountUsed() {
      return this.usedResourcesLoaded
        ? this.instances.reduce(
            (acc, instance) =>
              acc +
              instance.count *
                this.getInstanceDetail(instance.type, "required_volume_count"),
            0
          ) + Object.keys(this.localSpecs.volumes["nfs"]).length
        : 0;
    },
    volumeCountMax() {
      return this.quotas ? this.quotas.volume_count.max : 0;
    },
    volumeSizeUsed() {
      return this.usedResourcesLoaded
        ? this.instancesVolumeSizeUsed +
            Object.values(this.localSpecs.volumes.nfs).reduce(
              (acc, volume) => acc + volume.size,
              0
            )
        : 0;
    },
    volumeSizeMax() {
      return this.quotas ? this.quotas.volume_size.max : 0;
    },
    instancesVolumeSizeUsed() {
      return this.instances.reduce(
        (acc, instance) =>
          acc +
          instance.count *
            this.getInstanceDetail(instance.type, "required_volume_size"),
        0
      );
    },
    instances() {
      return this.localSpecs ? Object.values(this.localSpecs.instances) : [];
    },
    usedResourcesLoaded() {
      return this.localSpecs !== null && this.resourceDetails !== null;
    },
    applyButtonEnabled() {
      return (
        !this.loading &&
        this.validForm &&
        (this.dirtyForm ||
          [
            ClusterStatusCode.CREATED,
            ClusterStatusCode.BUILD_ERROR,
            ClusterStatusCode.PROVISIONING_ERROR,
            ClusterStatusCode.DESTROY_ERROR,
          ].includes(this.currentStatus))
      );
    },
  },
  methods: {
    changeHostnamePrefix(oldKey, newKey) {
      if (newKey != "" && !(newKey in this.localSpecs.instances)) {
        const instances = this.localSpecs.instances;
        const new_instances = {};
        for (const key of Object.keys(instances)) {
          if (key == oldKey) {
            new_instances[newKey] = instances[oldKey];
          } else {
            new_instances[key] = instances[key];
          }
        }
        this.localSpecs.instances = new_instances;
      }
    },
    changeVolumeName(oldKey, newKey) {
      if (newKey != "" && !(newKey in this.localSpecs.volumes.nfs)) {
        const nfs_volumes = this.localSpecs.volumes.nfs;
        const new_nfs_volumes = {};
        for (const key of Object.keys(nfs_volumes)) {
          if (key == oldKey) {
            new_nfs_volumes[newKey] = nfs_volumes[oldKey];
          } else {
            new_nfs_volumes[key] = nfs_volumes[key];
          }
        }
        this.localSpecs.volumes.nfs = new_nfs_volumes;
      }
    },
    publicTagRule(id) {
      var self = this;
      return function (tags) {
        if (
          self.localSpecs.instances[id].count > 0 &&
          tags.includes("public")
        ) {
          let newPublicIP = 0;
          for (let key in self.localSpecs.instances) {
            if (self.localSpecs.instances[key].tags.includes("public")) {
              newPublicIP += self.localSpecs.instances[key].count;
            }
          }
          if (self.existingCluster) {
            for (let key in self.initialSpecs.instances) {
              if (self.initialSpecs.instances[key].tags.includes("public")) {
                newPublicIP -= self.initialSpecs.instances[key].count;
              }
            }
          }
          return newPublicIP <= self.ipsCountMax || "Public IP quota exceeded";
        }
        return true;
      };
    },
    getTypes(tags) {
      if (this.possibleResources === null) {
        return [];
      }
      // Retrieve all available types
      // Then filter based on the selected tags
      let inst_types = this.possibleResources["types"];
      for (const tag of tags) {
        if (tag in this.possibleResources["tag_types"]) {
          const tag_types = new Set(this.possibleResources["tag_types"][tag]);
          inst_types = inst_types.filter((x) => tag_types.has(x));
        }
      }
      return inst_types;
    },
    getPossibleValues(fieldPath) {
      if (this.possibleResources === null) {
        return [];
      } else {
        return fieldPath
          .split(".")
          .reduce((acc, x) => acc[x], this.possibleResources);
      }
    },
    getInstanceDetail(instanceType, detailName, defaultValue = 0) {
      const matchingInstances = this.resourceDetails.instance_types.filter(
        (instanceTypeDetails) => instanceTypeDetails.name === instanceType
      );
      if (matchingInstances.length > 0) {
        return matchingInstances[0][detailName];
      } else {
        return defaultValue;
      }
    },
    countRule(value) {
      return value !== "" || "cannot be empty";
    },
    hostnamePrefixRule(id) {
      var self = this;
      return function (value) {
        if (value == "") {
          return "cannot be empty";
        }
        if (value != id && value in self.localSpecs.instances) {
          return "must be unique";
        }
        if (!/^[a-z][a-z0-9-]*$/.test(value)) {
          return "must match [a-z][-a-z0-9]*";
        }
        return true;
      };
    },
    volumeNameRule(id) {
      var self = this;
      return function (value) {
        if (value == "") {
          return "cannot be empty";
        }
        if (value != id && value in self.localSpecs.volumes.nfs) {
          return "must be unique";
        }
        if (!/^[a-z][a-z0-9-]*$/.test(value)) {
          return "must match [a-z][-a-z0-9]*";
        }
        return true;
      };
    },
    publicKeysRule(values) {
      if (values instanceof Array && values.length == 0) {
        return "Required - Paste a key then press enter. Only the comment section will be displayed.";
      }
      return (
        this.localSpecs.public_keys.every(
          (publicKey) => publicKey.match(SSH_PUBLIC_KEY_REGEX) !== null
        ) || "Invalid SSH public key"
      );
    },
    rmInstanceRow(id) {
      this.$delete(this.localSpecs.instances, id);
    },
    addInstanceRow() {
      const alphabet = "abcdefghijklmnopqrstuvwxyz";
      const keys = Object.keys(this.localSpecs.instances);
      const all_tags = new Set(
        Array.prototype.concat(
          ...keys.map((x) => this.localSpecs.instances[x].tags)
        )
      );
      let new_row_key;
      const stub = { count: 0, type: null, tags: [] };

      // All tags are filled, move on to copying the last row
      if (!all_tags.has("mgmt")) {
        new_row_key = "mgmt";
        stub["count"] = 1;
        stub["tags"] = ["mgmt", "puppet", "nfs"];
        stub["type"] = this.getTypes(stub["tags"])[0];
      } else if (!all_tags.has("login")) {
        new_row_key = "login";
        stub["count"] = 1;
        stub["tags"] = ["login", "proxy", "public"];
        stub["type"] = this.getTypes(stub["tags"])[0];
      } else if (!all_tags.has("node")) {
        new_row_key = "node";
        stub["count"] = 1;
        stub["tags"] = ["node"];
        stub["type"] = this.getTypes(stub["tags"])[0];
      } else {
        const key = keys[keys.length - 1];
        let prefix;
        let suffix;
        if (key.indexOf("-") != -1) {
          const prefix_split = key.split("-", 2);
          prefix = prefix_split[0];
          suffix = alphabet[(alphabet.indexOf(prefix_split[1]) + 1) % 26];
        } else {
          prefix = key;
          suffix = "a";
        }
        const stub_tags = this.localSpecs.instances[key].tags;
        const stub_type = this.localSpecs.instances[key].type;
        stub["count"] = 1;
        stub["type"] = stub_type;
        stub["tags"] = stub_tags;
        new_row_key = `${prefix}-${suffix}`;
      }
      this.$set(this.localSpecs.instances, new_row_key, stub);
    },
    addVolumeRow() {
      const nfs_volumes = new Set(Object.keys(this.localSpecs.volumes["nfs"]));
      let key = null;
      for (const vol of this.DEFAULT_VOLUMES) {
        if (!nfs_volumes.has(vol)) {
          key = vol;
          break;
        }
      }
      if (key === null) {
        const vol_array = Object.keys(this.localSpecs.volumes["nfs"]).filter(
          (value) => /^volume[0-9]{1,}$/.test(value)
        );
        if (vol_array.length > 0) {
          const index =
            Math.max(
              ...vol_array.map((value) => Number(value.replace(/^volume/, "")))
            ) + 1;
          key = `volume${index}`;
        } else {
          key = `volume1`;
        }
      }
      this.$set(this.localSpecs.volumes["nfs"], key, this.VOLUME_STUB);
    },
    rmVolumeRow(id) {
      this.$delete(this.localSpecs.volumes["nfs"], id);
    },
    apply() {
      this.$emit("apply");
    },
    async generateGuestPassword() {
      this.localSpecs.guest_passwd = generatePassword();
    },
    async changeCloudProject() {
      this.quotas = null;
      for (let key in this.localSpecs.instances) {
        this.localSpecs.instances[key].type = null;
      }
      this.localSpecs.image = null;
      await this.loadCloudResources();
    },

    async loadCloudResources() {
      this.loading = true;
      this.$emit("loading", this.loading);
      let availableResources = null;
      if (this.existingCluster) {
        availableResources = (
          await AvailableResourcesRepository.getHost(this.hostname)
        ).data;
      } else {
        availableResources = (
          await AvailableResourcesRepository.getCloud(this.localSpecs.cloud_id)
        ).data;
      }
      this.possibleResources = availableResources.possible_resources;
      this.quotas = availableResources.quotas;
      this.resourceDetails = availableResources.resource_details;
      this.loading = false;
      this.$emit("loading", this.loading);
    },
  },
};
</script>
<style scoped>
.hieradata-editor {
  font-size: 10pt;
  font-family: "Consolas", "Deja Vu Sans Mono", "Bitstream Vera Sans Mono",
    monospace;
}
</style>
