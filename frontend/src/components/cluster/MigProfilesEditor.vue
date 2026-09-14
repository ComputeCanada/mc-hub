<template>
  <div>
    <h4>MIG profiles</h4>
    <p class="text-caption text--secondary">Select a profile or type your own (for example, 1g.20gb).</p>
    <v-row v-for="(row, index) in rows" :key="row.id" dense align="center">
      <v-col cols="12" sm="7">
        <v-combobox
          :value="row.profile"
          :items="choices(row)"
          label="MIG profile"
          :aria-label="`MIG profile ${index + 1}`"
          @input="change(row, 'profile', $event)"
        />
      </v-col>
      <v-col cols="12" sm="5" class="d-flex align-center">
        <v-btn
          icon
          small
          :aria-label="`Decrease quantity for profile ${index + 1}`"
          :disabled="Number(row.count) <= 1"
          @click="change(row, 'count', Number(row.count) - 1)"
          ><v-icon>mdi-minus</v-icon></v-btn
        >
        <v-text-field
          :value="row.count"
          label="Quantity"
          type="number"
          min="1"
          step="1"
          :aria-label="`Quantity for profile ${index + 1}`"
          @input="change(row, 'count', $event)"
        />
        <v-btn
          icon
          small
          :aria-label="`Increase quantity for profile ${index + 1}`"
          :disabled="!canIncrease(row)"
          @click="change(row, 'count', Number(row.count) + 1)"
          ><v-icon>mdi-plus</v-icon></v-btn
        >
        <v-btn icon small class="ml-2" :aria-label="`Remove profile ${index + 1}`" @click="remove(index)">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-col>
    </v-row>
    <v-btn small outlined :disabled="used >= 7 || !!error" @click="add">Add profile</v-btn>
    <div class="mt-3" aria-live="polite">GPU slices: {{ used }} / 7 used</div>
    <v-progress-linear :value="Math.min((used / 7) * 100, 100)" :color="error ? 'error' : 'primary'" class="mt-1" />
    <v-input :value="error" :rules="[(value) => !value || value]" />
  </div>
</template>

<script>
export const DEFAULT_MIG_PROFILES = ["1g.5gb", "1g.10gb", "2g.10gb", "3g.20gb", "4g.20gb", "7g.40gb"];
const slices = (profile) => Number(/^([1-7])g\.[^\s]+$/.exec(profile || "")?.[1] || 0);
export default {
  name: "MigProfilesEditor",
  props: { value: { type: Object, default: () => ({}) }, additionalProfiles: { type: Array, default: () => [] } },
  data: () => ({ rows: [], nextId: 0, emittedValue: null }),
  computed: {
    profiles() {
      return [...new Set([...DEFAULT_MIG_PROFILES, ...this.additionalProfiles])];
    },
    used() {
      return this.rows.reduce((total, row) => total + slices(row.profile) * (Number(row.count) || 0), 0);
    },
    error() {
      const seen = new Set();
      for (const row of this.rows) {
        if (!slices(row.profile))
          return "Choose or enter a profile starting with 1g. through 7g., followed by a name without spaces.";
        if (seen.has(row.profile)) return "Each profile can appear only once. Adjust its quantity instead.";
        seen.add(row.profile);
        if (!Number.isInteger(Number(row.count)) || Number(row.count) < 1)
          return "Quantities must be positive whole numbers.";
      }
      return this.used > 7 ? "MIG profiles can use at most 7 GPU slices." : "";
    },
  },
  watch: {
    value: {
      immediate: true,
      deep: true,
      handler(value) {
        if (JSON.stringify(value || {}) === this.emittedValue) return;
        this.rows = Object.entries(value || {}).map(([profile, count]) => ({ id: this.nextId++, profile, count }));
      },
    },
    error: {
      immediate: true,
      handler(value) {
        this.$emit("invalid", !!value);
      },
    },
  },
  methods: {
    choices(row) {
      return this.profiles
        .filter((profile) => !this.rows.some((other) => other !== row && other.profile === profile))
        .filter(
          (profile) =>
            profile === row.profile ||
            this.used - slices(row.profile) * Number(row.count) + slices(profile) * Number(row.count) <= 7
        );
    },
    canIncrease(row) {
      return !this.error && slices(row.profile) > 0 && this.used + slices(row.profile) <= 7;
    },
    add() {
      this.rows.push({ id: this.nextId++, profile: "", count: 1 });
    },
    remove(index) {
      this.rows.splice(index, 1);
      this.publish();
    },
    change(row, key, value) {
      row[key] = key === "profile" ? (value || "").trim() : value;
      this.publish();
    },
    publish() {
      if (this.error) return;
      const value = Object.fromEntries(this.rows.map((row) => [row.profile, Number(row.count)]));
      this.emittedValue = JSON.stringify(value);
      this.$emit("input", value);
    },
  },
};
</script>
