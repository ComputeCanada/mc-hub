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
          <v-select
            v-model="magicCastle.image"
            :items="getPossibleValues('image')"
            label="Image"
          />
        </v-list-item>
        <v-list-item>
          <v-text-field
            v-model.number="magicCastle.nb_users"
            type="number"
            label="Number of users"
            :rules="[positiveNumberRule]"
          />
        </v-list-item>
      </v-list>
      <v-divider />

      <!-- Instances -->
      <v-subheader>Node instances</v-subheader>
      <v-list>
        <div :key="id" v-for="[id, label] in Object.entries(NODE_LABELS)">
          <v-list-item>
            <v-col cols="12" sm="3" class="pl-0">
              <p>{{ label }}</p>
            </v-col>

            <v-col cols="12" sm="5">
              <v-select
                :items="getPossibleValues(`instances.${id}.type`)"
                v-model="magicCastle.instances[id].type"
                label="Type"
                :rules="instanceRules"
              />
            </v-col>

            <v-col cols="12" sm="4">
              <v-text-field
                v-model.number="magicCastle.instances[id].count"
                type="number"
                label="Count"
                :rules="[greaterThanZeroRule, ...instanceRules]"
              />
            </v-col>
          </v-list-item>
          <v-divider />
        </div>
        <v-list-item>
          <v-col cols="12" sm="4">
            <resource-usage-display
              :max="instanceCountMax"
              :used="instanceCountUsed"
              title="Instances"
            />
          </v-col>
          <v-col cols="12" sm="4">
            <resource-usage-display
              :max="ramGbMax"
              :used="ramGbUsed"
              title="RAM"
              suffix="GB"
            />
          </v-col>
          <v-col cols="12" sm="4">
            <resource-usage-display
              :max="vcpuMax"
              :used="vcpuUsed"
              title="cores"
            />
          </v-col>
        </v-list-item>
        <v-divider />
      </v-list>

      <!-- Storage -->
      <v-subheader>Storage</v-subheader>
      <v-list>
        <v-list-item>
          <v-col cols="12" sm="3" class="pl-0">Type</v-col>
          <v-col cols="12" sm="9">
            <v-select
              :items="getPossibleValues('storage.type')"
              v-model="magicCastle.storage.type"
            />
          </v-col>
        </v-list-item>
        <v-divider />
        <div :key="id" v-for="[id, label] in Object.entries(STORAGE_LABELS)">
          <v-list-item>
            <v-col cols="12" sm="3" class="pl-0">{{ label }} size</v-col>
            <v-col cols="12" sm="9">
              <v-text-field
                v-model.number="magicCastle.storage[`${id}_size`]"
                type="number"
                suffix="GB"
                :rules="[volumeCountRule, volumeSizeRule, greaterThanZeroRule]"
              />
            </v-col>
          </v-list-item>
          <v-divider />
        </div>
        <v-list-item>
          <v-col cols="12" sm="6">
            <resource-usage-display
              :max="volumeCountMax"
              :used="volumeCountUsed"
              title="volumes"
            />
          </v-col>
          <v-col cols="12" sm="6">
            <resource-usage-display
              :max="volumeSizeMax"
              :used="volumeSizeUsed"
              title="volume storage"
              suffix="GB"
            />
          </v-col>
        </v-list-item>
        <v-divider />
      </v-list>

      <!-- Networking & security -->
      <v-subheader>Networking and security</v-subheader>
      <v-list>
        <v-list-item>
          <public-key-input
            v-model="magicCastle.public_keys"
            :rules="[publicKeysRule]"
          />
        </v-list-item>
        <v-list-item>
          <v-text-field
            v-model="magicCastle.guest_passwd"
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
        <v-list-item>
          <v-select
            :items="getPossibleValues('os_floating_ips')"
            v-model="magicCastle.os_floating_ips[0]"
            :rules="[floatingIpProvidedRule, floatingIpAvailableRule]"
            label="OpenStack floating IP"
          />
        </v-list-item>
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
import { generatePassword } from "@/models/utils";
import ClusterStatusCode from "@/models/ClusterStatusCode";
import ResourceUsageDisplay from "@/components/ui/ResourceUsageDisplay";
import PublicKeyInput from "@/components/ui/PublicKeyInput";

const EXTERNAL_STORAGE_VOLUME_COUNT = 3;
const MB_PER_GB = 1024;
const MINIMUM_PASSWORD_LENGTH = 8;
const CLUSTER_NAME_REGEX = /^[a-z][a-z0-9]*$/;
const SSH_PUBLIC_KEY_REGEX = /^(ssh-rsa AAAAB3NzaC1yc2|ecdsa-sha2-nistp256 AAAAE2VjZHNhLXNoYTItbmlzdHAyNT|ecdsa-sha2-nistp384 AAAAE2VjZHNhLXNoYTItbmlzdHAzODQAAAAIbmlzdHAzOD|ecdsa-sha2-nistp521 AAAAE2VjZHNhLXNoYTItbmlzdHA1MjEAAAAIbmlzdHA1Mj|ssh-ed25519 AAAAC3NzaC1lZDI1NTE5|ssh-dss AAAAB3NzaC1kc3)[0-9A-Za-z+/]+[=]{0,3}( .*)?$/;

export default {
  name: "ClusterEditor",
  components: {
    ResourceUsageDisplay,
    PublicKeyInput
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
      NODE_LABELS: {
        mgmt: "Management",
        login: "Login",
        node: "Compute"
      },
      STORAGE_LABELS: {
        home: "Home",
        project: "Project",
        scratch: "Scratch"
      },

      validForm: true,
      initialMagicCastle: null,

      clusterNameRegexRule: value =>
        value.match(CLUSTER_NAME_REGEX) !== null ||
        "The cluster name must have only lowercase alphanumeric characters and start with a letter",
      greaterThanZeroRule: value =>
        (typeof value === "number" && value > 0) || "Must be greater than zero",
      positiveNumberRule: value =>
        (typeof value === "number" && value >= 0) ||
        "Must be a positive number",
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


      // Floating IPs
      // Must be set to the first possible value in all cases (either "Automatic allocation" or a specific IP address)
      if (possibleResources.os_floating_ips.length > 0) {
        this.magicCastle.os_floating_ips = [
          possibleResources.os_floating_ips[0]
        ];
        this.initialMagicCastle.os_floating_ips = [
          possibleResources.os_floating_ips[0]
        ];
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
      this.generateGuestPassword();
    }
    this.initialMagicCastle = cloneDeep(this.magicCastle);
  },
  beforeDestroy() {
    this.$disableUnloadConfirmation();
  },
  computed: {
    applyRunning() {
      return [
        ClusterStatusCode.DESTROY_RUNNING,
        ClusterStatusCode.BUILD_RUNNING
      ].includes(this.currentStatus);
    },
    dirtyForm() {
      return !isEqual(this.initialMagicCastle, this.magicCastle);
    },
    clusterName() {
      return this.hostname.split(".")[0];
    },
    domainRule() {
      return (
        (this.possibleResources &&
          this.possibleResources.domain.includes(this.magicCastle.domain)) ||
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
      return (
        this.volumeCountUsed <= this.volumeCountMax ||
        "Number of volumes exceeds maximum"
      );
    },
    volumeSizeRule() {
      return (
        this.volumeSizeUsed <= this.volumeSizeMax ||
        "Volume storage exceeds maximum"
      );
    },
    publicKeysRule() {
      return (
        isEqual(this.magicCastle.public_keys, [""]) ||
        this.magicCastle.public_keys.every(publicKey => publicKey.match(SSH_PUBLIC_KEY_REGEX) !== null) ||
        "Invalid SSH public key"
      );
    },
    floatingIpProvidedRule() {
      return (
        this.magicCastle.os_floating_ips.length > 0 || "No floating IP provided"
      );
    },
    floatingIpAvailableRule() {
      return (
        (this.possibleResources &&
          this.magicCastle &&
          this.possibleResources.os_floating_ips.includes(
            this.magicCastle.os_floating_ips[0]
          )) ||
        "Floating IP not available"
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
          ) + EXTERNAL_STORAGE_VOLUME_COUNT
        : 0;
    },
    volumeCountMax() {
      return this.quotas ? this.quotas.volume_count.max : 0;
    },
    volumeSizeUsed() {
      return this.usedResourcesLoaded
        ? this.instancesVolumeSizeUsed +
            this.magicCastle.storage.home_size +
            this.magicCastle.storage.project_size +
            this.magicCastle.storage.scratch_size
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
    }
  },
  methods: {
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
    },
    generateGuestPassword() {
      this.magicCastle.guest_passwd = generatePassword();
    }
  }
};
</script>
