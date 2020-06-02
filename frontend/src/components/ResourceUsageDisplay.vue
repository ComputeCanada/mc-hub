<template>
  <div class="text-center d-flex flex-column align-center">
    Used {{ title }}
    <v-progress-circular :color="usageColor" :value="usagePercentage" :size="60" :width="5"
      >{{ usagePercentage }} %
    </v-progress-circular>
    <span class="grey--text mt-2">{{ used }} {{ suffix }} / {{ max }} {{ suffix }}</span>
  </div>
</template>

<script>
export default {
  name: "ResourceUsageDisplay",
  props: {
    used: { type: Number, required: true },
    max: { type: Number, required: true },
    title: { type: String, required: true },
    suffix: {
      type: String,
      default: ""
    }
  },
  computed: {
    usagePercentage() {
      if (this.max === 0) {
        return 0;
      } else {
        return Math.round((100 * this.used) / this.max);
      }
    },
    usageColor() {
      return this.usagePercentage < 100 ? "green" : "red";
    }
  }
};
</script>

<style scoped></style>
