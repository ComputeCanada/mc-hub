<template>
  <v-select :items="items" v-model="selected" label="type" :rules="rules">
    <template #item="{ item }">
      <v-list-item-content v-if="typeof item !== 'undefined'">
        <v-list-item-title>{{ item.text }}</v-list-item-title>
        <v-list-item-subtitle>{{ item.description }}</v-list-item-subtitle>
      </v-list-item-content>
    </template>
  </v-select>
</template>

<script>
const TYPE_REGEX =
  /^(?:g(?<gpu>[0-9]+)(?:-(?<gpu_ram>[0-9.]+)gb)?-)?[pc](?<cpu>[0-9]+)-(?:(?<ram>[0-9.]+)gb)(?:-(?<disk>[0-9.]+))?/;
const TYPE_CATEGORIES = [
  {
    prefix: "p",
    name: "Persistent storage types",
  },
  {
    prefix: "c",
    name: "Compute types",
  },
  {
    prefix: "g",
    name: "GPU types",
  },
];
export default {
  name: "TypeSelect",
  props: {
    value: {
      type: String,
    },
    types: {
      type: Array,
      required: true,
    },
    rules: {
      type: Array,
      default: () => [],
    },
  },
  data() {
    return {
      selected: this.value,
    };
  },
  watch: {
    selected: function (newValue) {
      this.$emit("input", newValue);
    },
    value: function (newValue) {
      this.selected = newValue;
    },
  },
  computed: {
    items() {
      let items = [];
      TYPE_CATEGORIES.forEach(({ prefix, name }) => {
        const types = this.types.filter((type) => {
          type.startsWith(prefix) && type.match(TYPE_REGEX) != null;
        });
        if (types.length > 0) {
          if (items.length > 0) {
            items.push({ divider: true });
          }
          items.push({ header: name });
          items = items.concat(
            types.map((type) => {
              return {
                text: type,
                description: this.getTypeDescription(type),
              };
            })
          );
        }
      });
      return items;
    },
  },
  methods: {
    getTypeDescription(typeName) {
      let namedGroupMatches = {};
      const typeMatchRegex = typeName.match(TYPE_REGEX);
      if (typeMatchRegex != null) {
        namedGroupMatches = typeMatchRegex.groups;
      }

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
    },
  },
};
</script>

<style scoped></style>
