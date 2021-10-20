<template>
  <v-select :items="items" v-model="value" :label="label" :rules="rules">
    <template #item="{item}">
      <v-list-item-content v-if="typeof item !== 'undefined'">
        <v-list-item-title>{{ item.text }}</v-list-item-title>
        <v-list-item-subtitle>{{ item.description }}</v-list-item-subtitle>
      </v-list-item-content>
    </template>
  </v-select>
</template>

<script>
const FLAVOR_REGEX = /^(?:g(?<gpu>[0-9]+)(?:-(?<gpu_ram>[0-9.]+)gb)?-)?[pc](?<cpu>[0-9]+)-(?:(?<ram>[0-9.]+)gb)(?:-(?<disk>[0-9.]+))?/;
const FLAVOR_CATEGORIES = [
  {
    prefix: "p",
    name: "Persistent storage flavors"
  },
  {
    prefix: "c",
    name: "Compute flavors"
  },
  {
    prefix: "g",
    name: "GPU flavors"
  }
];
export default {
  name: "FlavorSelect",
  props: {
    value: {
      type: String,
      required: true
    },
    flavors: {
      type: Array,
      required: true
    },
    rules: {
      type: Array,
      default: () => []
    }
  },
  watch: {
    value(newValue) {
      this.$emit("input", newValue);
    }
  },
  computed: {
    items() {
      let items = [];
      FLAVOR_CATEGORIES.forEach(({ prefix, name }) => {
        const flavors = this.flavors.filter(flavor => flavor.startsWith(prefix));
        if (flavors.length > 0) {
          if (items.length > 0) {
            items.push({ divider: true });
          }
          items.push({ header: name });
          items = items.concat(
            flavors.map(flavor => {
              return { text: flavor, description: this.getFlavorDescription(flavor) };
            })
          );
        }
      });
      return items;
    }
  },
  methods: {
    getFlavorDescription(flavorName) {
      const namedGroupMatches = flavorName.match(FLAVOR_REGEX).groups;

      let descriptionElements = [];
      if (typeof namedGroupMatches["gpu"] !== "undefined") {
        let gpuDescription = `${namedGroupMatches.gpu} vGPU`;
        if (typeof namedGroupMatches["gpu_ram"] !== "undefined") {
          gpuDescription += ` (${namedGroupMatches.gpu_ram} GB)`;
        }
        descriptionElements.push(gpuDescription);
      }
      descriptionElements.push(`${namedGroupMatches.cpu} vCPU`);
      descriptionElements.push(`${namedGroupMatches.ram} GB RAM`);
      if (typeof namedGroupMatches["disk"] !== "undefined") {
        descriptionElements.push(`${namedGroupMatches.disk} GB ephemeral storage`);
      }

      return descriptionElements.join(", ");
    }
  }
};
</script>

<style scoped></style>
