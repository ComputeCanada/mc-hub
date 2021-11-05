<template>
  <div>
    <v-form v-model="validForm">
      <v-subheader>General configuration</v-subheader>
      <v-list class="pt-0">
        <v-list-item v-if="!existingCluster">
          <v-text-field
            v-model="magicCastle.cluster_name"
            label="Cluster name"
            :rules="[clusterNameRegexRule]"
            validate-on-blur
          />
        </v-list-item>
        <v-list-item v-if="!existingCluster">
          <v-select
            v-model="magicCastle.domain"
            :items="getPossibleValues('domain')"
            label="Domain"
            :rules="[domainRule]"
          />
        </v-list-item>
        <v-list-item>
          <v-select v-model="magicCastle.image" :items="getPossibleValues('image')" label="Image" />
        </v-list-item>
      </v-list>
      <v-divider />

      <!-- Instances -->
      <v-list class="pt-0">
        <v-list-item>
          <v-col cols="12" sm="3">
            <resource-usage-display :max="instanceCountMax" :used="instanceCountUsed" title="Instances" />
          </v-col>
          <v-col cols="12" sm="3">
            <resource-usage-display :max="ramGbMax" :used="ramGbUsed" title="RAM" suffix="GB" />
          </v-col>
          <v-col cols="12" sm="3">
            <resource-usage-display :max="vcpuMax" :used="vcpuUsed" title="cores" />
          </v-col>
          <v-col cols="12" sm="3">
            <resource-usage-display :max="volumeCountMax" :used="volumeCountUsed" title="volumes" />
          </v-col>
        </v-list-item>
      </v-list>
      <v-list>
        <div :key="id" v-for="id in DEFAULT_INSTANCE_PREFIX">
          <v-list-item>
            <v-col cols="12" sm="1" class="pt-0">
              <v-text-field
                v-model.number="magicCastle.instances[id].count"
                type="number"
                prefix="x"
                :rules="instanceRules"
                dir="rtl"
                min="0"
                reverse
              />
            </v-col>
            <v-col cols="12" sm="3" class="pt-0">
              <v-text-field :value="id" label="hostname prefix" readonly />
            </v-col>
            <v-col cols="12" sm="3" class="pt-0">
              <flavor-select
                :flavors="getPossibleValues(`instances.${id}.type`)"
                v-model="magicCastle.instances[id].type"
                label="Type"
                :rules="instanceRules"
              />
            </v-col>
            <v-col cols="12" sm="5" class="pt-0">
              <v-combobox v-model="magicCastle.instances[id].tags" :items="TAGS" label="tags" multiple></v-combobox>
            </v-col>
          </v-list-item>
        </div>
      </v-list>
      <v-divider />
      <!-- Volumes -->
      <v-list>
        <v-list-item>
          <v-col cols="12" sm="12">
            <resource-usage-display :max="volumeSizeMax" :used="volumeSizeUsed" title="volume storage" suffix="GB" />
          </v-col>
        </v-list-item>
      </v-list>
      <v-list>
        <div :key="id" v-for="id in DEFAULT_VOLUMES">
          <v-list-item>
            <v-col cols="12" sm="3" class="pt-0">
              <v-text-field :value="id" label="volume name" readonly />
            </v-col>
            <v-col cols="12" sm="2" class="pt-0">
              <v-text-field
                v-model.number="magicCastle.volumes.nfs[id].size"
                type="number"
                label="size"
                prefix="GB"
                :rules="[volumeCountRule, volumeSizeRule, greaterThanZeroRule]"
                min="0"
                dir="rtl"
                reverse
              />
            </v-col>
          </v-list-item>
        </div>
        <v-divider />
      </v-list>

      <!-- Networking & security -->
      <v-subheader>Networking and security</v-subheader>
      <v-list>
        <v-list-item>
          <v-combobox
          v-model="magicCastle.public_keys"
          label="SSH Keys"
          multiple
          chips
          append-icon
          clearable
          deletable-chips
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
              {{ data.item.split(" ").length > 2 ? data.item.split(" ")[2] : data.item.slice(0, 15) + "..." + data.item.slice(-5) }}
              </v-chip>
          </template>
          </v-combobox>
        </v-list-item>
        <v-list-item>
          <v-text-field v-model.number="magicCastle.nb_users" type="number" label="Number of guest users" min="0" />
        </v-list-item>
        <v-list-item>
          <v-text-field v-model="magicCastle.guest_passwd" label="Guest password" :rules="[passwordLengthRule]" />
          <v-tooltip bottom>
            <template #activator="{ on, attrs }">
              <v-btn icon v-bind="attrs" v-on="on" @click="generateGuestPassword()">
                <v-icon>mdi-refresh</v-icon>
              </v-btn>
            </template>
            <span>Generate new password</span>
          </v-tooltip>
        </v-list-item>
        <v-list-group prepend-icon="mdi-script-text-outline">
          <template #activator>
            <v-list-item-content>
              <v-list-item-title>Additional puppet configuration (optional)</v-list-item-title>
            </v-list-item-content>
          </template>
          <v-list-item>
            <v-list-item-content>
              <span class="mb-4" style="line-height: 18pt;"
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
                v-model="magicCastle.hieradata"
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
        <v-btn @click="apply" color="primary" class="ma-2" :disabled="!applyButtonEnabled" large>Apply</v-btn>
        <v-btn to="/" class="ma-2" :disabled="loading" large outlined color="primary">Cancel</v-btn>
      </div>
    </v-form>
  </div>
</template>

<script>
import { cloneDeep, isEqual } from "lodash";
import { generatePassword, generatePetName } from "@/models/utils";
import ClusterStatusCode from "@/models/ClusterStatusCode";
import UserRepository from "@/repositories/UserRepository";
import ResourceUsageDisplay from "@/components/ui/ResourceUsageDisplay";
import FlavorSelect from "./FlavorSelect";
import CodeEditor from "@/components/ui/CodeEditor";

const MB_PER_GB = 1024;
const MINIMUM_PASSWORD_LENGTH = 8;
const CLUSTER_NAME_REGEX = /^[a-z]([a-z0-9-]*[a-z0-9]+)?$/;
const SSH_PUBLIC_KEY_REGEX = /^(ssh-rsa AAAAB3NzaC1yc2|ecdsa-sha2-nistp256 AAAAE2VjZHNhLXNoYTItbmlzdHAyNT|ecdsa-sha2-nistp384 AAAAE2VjZHNhLXNoYTItbmlzdHAzODQAAAAIbmlzdHAzOD|ecdsa-sha2-nistp521 AAAAE2VjZHNhLXNoYTItbmlzdHA1MjEAAAAIbmlzdHA1Mj|ssh-ed25519 AAAAC3NzaC1lZDI1NTE5|ssh-dss AAAAB3NzaC1kc3)[0-9A-Za-z+/]+[=]{0,3}( .*)?$/;

export default {
  name: "ClusterEditor",
  components: {
    CodeEditor,
    FlavorSelect,
    ResourceUsageDisplay,
  },
  props: {
    magicCastle: {
      type: Object,
      required: true
    },
    hostname: String,
    loading: {
      type: Boolean,
      required: true
    },
    existingCluster: {
      type: Boolean,
      required: true
    },
    quotas: {
      type: Object
    },
    resourceDetails: {
      type: Object
    },
    possibleResources: {
      type: Object
    },
    currentStatus: {
      type: String
    }
  },
  data: function() {
    return {
      DEFAULT_INSTANCE_PREFIX: ["mgmt", "login", "node"],
      DEFAULT_VOLUMES: ["home", "project", "scratch"],
      TAGS: ["mgmt", "puppet", "nfs", "login", "proxy", "public", "node"],
      validForm: true,
      initialMagicCastle: null,

      clusterNameRegexRule: value =>
        value.match(CLUSTER_NAME_REGEX) !== null ||
        "Must contain lowercase alphanumeric characters and start with a letter. It can also include dashes.",
      greaterThanZeroRule: value => (typeof value === "number" && value > 0) || "Must be greater than zero",
      positiveNumberRule: value => (typeof value === "number" && value >= 0) || "Must be a positive number",
      passwordLengthRule: value =>
        value.length >= MINIMUM_PASSWORD_LENGTH ||
        `The password must be at least ${MINIMUM_PASSWORD_LENGTH} characters long`
    };
  },
  watch: {
    possibleResources(possibleResources) {
      // We set default values for select boxes based on possible resources fetched from the API

      // Domain
      if (this.magicCastle.domain === null && possibleResources.domain.length > 0) {
        this.magicCastle.domain = possibleResources.domain[0];
        this.initialMagicCastle.domain = possibleResources.domain[0];
      }

      // Images
      if (this.magicCastle.image === null && possibleResources.image.length > 0) {
        // MC is not compatible with CentOS 8 currently. Therefore, we choose another image by default.
        const image = possibleResources.image.filter(image => image.match(/^(?!CentOS-8|centos8).*$/i))[0];
        this.magicCastle.image = image;
        this.initialMagicCastle.image = image;
      }

      // Instance types
      if (this.magicCastle.instances.login.type === null && possibleResources.instances.login.type.length > 0) {
        this.magicCastle.instances.login.type = possibleResources.instances.login.type[0];
        this.initialMagicCastle.instances.login.type = possibleResources.instances.login.type[0];
      }
      if (this.magicCastle.instances.mgmt.type === null && possibleResources.instances.mgmt.type.length > 0) {
        this.magicCastle.instances.mgmt.type = possibleResources.instances.mgmt.type[0];
        this.initialMagicCastle.instances.mgmt.type = possibleResources.instances.mgmt.type[0];
      }
      if (this.magicCastle.instances.node.type === null && possibleResources.instances.node.type.length > 0) {
        this.magicCastle.instances.node.type = possibleResources.instances.node.type[0];
        this.initialMagicCastle.instances.node.type = possibleResources.instances.node.type[0];
      }
    },
    dirtyForm(dirty) {
      if (dirty) {
        this.$enableUnloadConfirmation();
      } else {
        this.$disableUnloadConfirmation();
      }
    }
  },
  created() {
    if (!this.existingCluster) {
      this.magicCastle.cluster_name = generatePetName();
      this.magicCastle.guest_passwd = generatePassword();
      this.magicCastle.instances["mgmt"].tags = ["mgmt", "nfs", "puppet"];
      this.magicCastle.instances["login"].tags = ["login", "proxy", "public"];
      this.magicCastle.instances["node"].tags = ["node"];
    }
    this.initialMagicCastle = cloneDeep(this.magicCastle);
  },
  async mounted() {
    if (!this.existingCluster) {
      let public_keys = [];
      try {
        public_keys = (await UserRepository.getCurrent()).data.public_keys;
      } catch (e) {
        console.log("User SSH public keys be found");
      }
      if (public_keys != null ) {
        this.magicCastle.public_keys = public_keys.filter(key => key.match(SSH_PUBLIC_KEY_REGEX));
      }
    }
  },
  beforeDestroy() {
    this.$disableUnloadConfirmation();
  },
  computed: {
    applyRunning() {
      return [ClusterStatusCode.DESTROY_RUNNING, ClusterStatusCode.BUILD_RUNNING].includes(this.currentStatus);
    },
    dirtyForm() {
      return !this.existingCluster || !isEqual(this.initialMagicCastle, this.magicCastle);
    },
    clusterName() {
      return this.hostname.split(".")[0];
    },
    domainRule() {
      return (
        (this.possibleResources && this.possibleResources.domain.includes(this.magicCastle.domain)) ||
        "Invalid domain provided"
      );
    },
    instanceRules() {
      return [
        this.ramGbUsed <= this.ramGbMax || "Ram exceeds maximum",
        this.vcpuUsed <= this.vcpuMax || "Cores exceeds maximum"
      ];
    },
    volumeCountRule() {
      return this.volumeCountUsed <= this.volumeCountMax || "Number of volumes exceeds maximum";
    },
    volumeSizeRule() {
      return this.volumeSizeUsed <= this.volumeSizeMax || "Volume storage exceeds maximum";
    },
    publicKeysRule() {
      return (
        this.magicCastle.public_keys.every(publicKey => publicKey.match(SSH_PUBLIC_KEY_REGEX) !== null) ||
        "Invalid SSH public key"
      );
    },
    instanceCountUsed() {
      return this.usedResourcesLoaded ? this.instances.reduce((acc, instance) => acc + instance.count, 0) : 0;
    },
    instanceCountMax() {
      return this.quotas ? this.quotas.instance_count.max : 0;
    },
    ramGbUsed() {
      return this.usedResourcesLoaded
        ? this.instances.reduce(
            (acc, instance) => acc + instance.count * this.getInstanceDetail(instance.type, "ram"),
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
            (acc, instance) => acc + instance.count * this.getInstanceDetail(instance.type, "vcpus"),
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
            (acc, instance) => acc + instance.count * this.getInstanceDetail(instance.type, "required_volume_count"),
            0
          ) + Object.keys(this.magicCastle.volumes["nfs"]).length
        : 0;
    },
    volumeCountMax() {
      return this.quotas ? this.quotas.volume_count.max : 0;
    },
    volumeSizeUsed() {
      return this.usedResourcesLoaded
        ? this.instancesVolumeSizeUsed +
            this.magicCastle.volumes["nfs"]["home"].size +
            this.magicCastle.volumes["nfs"]["project"].size +
            this.magicCastle.volumes["nfs"]["scratch"].size
        : 0;
    },
    volumeSizeMax() {
      return this.quotas ? this.quotas.volume_size.max : 0;
    },
    instancesVolumeSizeUsed() {
      return this.instances.reduce(
        (acc, instance) => acc + instance.count * this.getInstanceDetail(instance.type, "required_volume_size"),
        0
      );
    },
    instances() {
      return this.magicCastle ? Object.values(this.magicCastle.instances) : [];
    },
    usedResourcesLoaded() {
      return this.magicCastle !== null && this.resourceDetails !== null;
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
            ClusterStatusCode.DESTROY_ERROR
          ].includes(this.currentStatus))
      );
    },
  },
  methods: {
    getPossibleValues(fieldPath) {
      if (this.possibleResources === null) {
        return [];
      } else {
        return fieldPath.split(".").reduce((acc, x) => acc[x], this.possibleResources);
      }
    },
    getInstanceDetail(instanceType, detailName, defaultValue = 0) {
      const matchingInstances = this.resourceDetails.instance_types.filter(
        instanceTypeDetails => instanceTypeDetails.name === instanceType
      );
      if (matchingInstances.length > 0) {
        return matchingInstances[0][detailName];
      } else {
        return defaultValue;
      }
    },
    apply() {
      this.$emit("apply");
    }
  }
};
</script>
<style scoped>
.hieradata-editor {
  font-size: 10pt;
  font-family: "Consolas", "Deja Vu Sans Mono", "Bitstream Vera Sans Mono", monospace;
}
</style>
