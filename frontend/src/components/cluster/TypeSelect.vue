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
const GPU_REGEX = /^g(?<gpu>[0-9]+)(?:-(?<gpu_ram>[0-9.]+)gb)?-/;
const DISK_REGEX = /[pc][0-9]+-[0-9.]+gb-(?<disk>[0-9.]+)/;
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
        const types = this.types.filter((type) => type.name.startsWith(prefix));
        if (types.length > 0) {
          if (items.length > 0) {
            items.push({ divider: true });
          }
          items.push({ header: name });
          items = items.concat(
            types.map((type) => {
              return {
                text: type.name,
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
    getTypeDescription(typeObj) {
      let descriptionElements = [];

      const gpuMatch = typeObj.name.match(GPU_REGEX);
      if (gpuMatch) {
        let gpuDescription = `${gpuMatch.groups.gpu} vGPU`;
        if (gpuMatch.groups.gpu_ram) {
          gpuDescription += ` (${gpuMatch.groups.gpu_ram} GB)`;
        }
        descriptionElements.push(gpuDescription);
      }

      descriptionElements.push(`${typeObj.vcpus} vCPU`);
      descriptionElements.push(`${typeObj.ram / 1024} GB RAM`);

      const diskMatch = typeObj.name.match(DISK_REGEX);
      if (diskMatch) {
        descriptionElements.push(`${diskMatch.groups.disk} GB ephemeral storage`);
      }

      return descriptionElements.join(", ");
    },
  },
};
</script>

<style scoped></style>
