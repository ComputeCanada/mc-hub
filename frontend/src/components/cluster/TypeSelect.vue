<template>
  <v-select
    :items="items"
    v-model="selected"
    :label="types.some((type) => type.quota_pool) ? 'Instance type' : 'type'"
    :rules="rules"
    :loading="loading"
    :disabled="loading"
    :no-data-text="loading ? 'Loading instance types…' : 'No instance types available for this definition'"
  >
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
  {
    prefix: "ha",
    name: "High availability types",
  },
];
export default {
  name: "TypeSelect",
  props: {
    loading: { type: Boolean, default: false },
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
      if (this.types.some((type) => type.quota_pool)) {
        return [...this.types]
          .sort(
            (a, b) =>
              (a.hourly_price_usd == null ? Infinity : Number(a.hourly_price_usd)) -
              (b.hourly_price_usd == null ? Infinity : Number(b.hourly_price_usd))
          )
          .map((type) => ({
            text: type.name,
            value: type.name,
            disabled: !!type.unavailable,
            description: this.getTypeDescription(type),
          }));
      }
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

      const otherTypes = this.types.filter(
        (type) => !TYPE_CATEGORIES.some(({ prefix }) => type.name.startsWith(prefix))
      );
      if (otherTypes.length > 0) {
        if (items.length > 0) {
          items.push({ divider: true });
        }
        items.push({ header: "Other types" });
        items = items.concat(
          otherTypes.map((type) => {
            return {
              text: type.name,
              description: this.getTypeDescription(type),
            };
          })
        );
      }
      return items;
    },
  },
  methods: {
    getTypeDescription(typeObj) {
      if (typeObj.quota_pool) {
        const details = [`${typeObj.vcpus} vCPU`, `${typeObj.ram / 1024} GiB RAM`];
        for (const gpu of typeObj.gpus || []) {
          const partition = gpu.partition_size;
          const fractional = partition > 0 && partition < 1;
          const denominator = fractional ? Math.round(1 / partition) : 1;
          const share = fractional
            ? (Math.abs(1 / denominator - partition) < 1e-9 ? `1/${denominator}` : String(partition)) + " of "
            : "";
          const count = gpu.count > 0 ? `${gpu.count} × ` : "";
          const memory =
            gpu.memory_mib == null ? "" : ` (${gpu.memory_mib / 1024} GiB VRAM${gpu.count > 0 ? " each" : ""})`;
          details.push(`${count}${share}${gpu.manufacturer} ${gpu.name}${fractional ? " GPU" : ""}${memory}`);
        }
        details.push(
          typeObj.hourly_price_usd == null
            ? "Price unavailable"
            : `$${Number(typeObj.hourly_price_usd).toLocaleString("en-US", { maximumFractionDigits: 10 })}/hour`
        );
        if (typeObj.unavailable) details.push("Unavailable for this definition — select a replacement");
        return details.join(" · ");
      }
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
      const ramGb = Number((typeObj.ram / 1024).toFixed(2));
      descriptionElements.push(`${ramGb} GB RAM`);

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
