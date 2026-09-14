<template>
  <v-sheet outlined rounded class="pa-4 mb-4">
    <h3>Optional settings for {{ name }}</h3>
    <p class="text--secondary">
      Applies to all {{ instance.count }} instances. Clear a field to use its inherited or automatic value.
    </p>
    <v-alert v-if="provider === 'aws'" type="info" dense>
      AWS feasibility checks currently reject instance overrides. Clear optional settings before saving an AWS cluster.
    </v-alert>
    <section v-for="section in sections" :key="section.title">
      <h4 class="mt-3">{{ section.title }}</h4>
      <v-row>
        <v-col v-for="field in section.fields" :key="field.key" cols="12" :sm="field.fullWidth ? 12 : 6">
          <v-combobox
            v-if="field.kind === 'list'"
            :value="instance[field.key] || []"
            :label="field.label"
            multiple
            chips
            deletable-chips
            clearable
            @input="set(field.key, $event)"
          />
          <v-select
            v-else-if="field.options"
            :value="instance[field.key]"
            :items="field.options"
            :label="field.label"
            clearable
            :placeholder="field.key === 'image' ? 'Use global image' : 'Automatic'"
            @change="set(field.key, $event)"
          />
          <mig-profiles-editor
            v-else-if="field.kind === 'mig'"
            :value="instance.mig"
            :additional-profiles="additionalMigProfiles"
            @input="set('mig', Object.keys($event).length ? $event : null)"
            @invalid="migInvalid = $event"
          />
          <v-text-field
            v-else
            :value="instance[field.key]"
            :label="field.label"
            :suffix="field.unit"
            :type="field.kind === 'number' ? 'number' : 'text'"
            :min="field.min"
            :step="field.step || 1"
            :hint="field.hint || 'Inherited or automatic when unset'"
            persistent-hint
            clearable
            :rules="field.kind === 'number' ? [numberRule(field)] : []"
            @input="set(field.key, $event, field.kind)"
          />
        </v-col>
      </v-row>
    </section>
  </v-sheet>
</template>

<script>
import MigProfilesEditor from "./MigProfilesEditor";

const number = (key, label, unit, min = 0) => ({ key, label, unit, min, kind: "number" });
export default {
  name: "InstanceSettings",
  components: { MigProfilesEditor },
  props: {
    instance: { type: Object, required: true },
    name: String,
    provider: String,
    hasGpu: { type: Boolean, default: false },
    images: { type: Array, default: () => [] },
    additionalMigProfiles: { type: Array, default: () => [] },
  },
  data: () => ({ migInvalid: false }),
  watch: {
    hasErrors: {
      immediate: true,
      handler(value) {
        this.$emit("invalid", value);
      },
    },
  },
  computed: {
    hasErrors() {
      return (
        (this.hasGpu && this.migInvalid) ||
        this.sections.some((section) =>
          section.fields.some((field) => {
            if (field.kind === "number") return this.numberRule(field)(this.instance[field.key]) !== true;
            return false;
          })
        )
      );
    },
    sections() {
      const sections = [
        {
          title: "Image & storage",
          fields: [
            {
              key: "image",
              label: "Image",
              options: this.images,
            },
            number("disk_size", "Root disk size", "GiB", 1),
          ],
        },
        {
          title: this.hasGpu ? "Scheduling & GPUs" : "Scheduling",
          fields: [
            ...(this.hasGpu
              ? [
                  {
                    key: "mig",
                    label: "MIG profiles",
                    kind: "mig",
                    fullWidth: true,
                    hint: 'Profile/count map, e.g. {"1g.5gb": 2}. Requires a supported GPU and x86-64 CPU.',
                  },
                ]
              : []),
            { key: "features", label: "Slurm features", kind: "list", fullWidth: true },
          ],
        },
      ];
      const spot = (this.instance.tags || []).includes("spot");
      let fields = [];
      if (this.provider === "aws" && spot)
        fields = [
          {
            key: "wait_for_fulfillment",
            label: "Wait for fulfillment",
            options: [
              { text: "Yes", value: true },
              { text: "No", value: false },
            ],
          },
          { key: "spot_type", label: "Spot request type", options: ["one-time", "persistent"] },
          {
            key: "instance_interruption_behavior",
            label: "Interruption behavior",
            options: ["stop", "terminate", "hibernate"],
          },
          { key: "spot_price", label: "Spot price" },
          number("block_duration_minutes", "Block duration", "minutes"),
        ];
      if (this.provider === "azure" && spot)
        fields = [
          { ...number("max_bid_price", "Maximum bid price", undefined, -1), step: "any" },
          { key: "eviction_policy", label: "Eviction policy", options: ["Deallocate", "Delete"] },
        ];
      if (this.provider === "incus") fields = [{ key: "target", label: "Cluster member" }];
      if (fields.length) sections.push({ title: "Provider options", fields });
      return sections;
    },
  },
  methods: {
    set(key, value, kind) {
      if (value === "" || value == null || (Array.isArray(value) && !value.length)) this.$delete(this.instance, key);
      else this.$set(this.instance, key, kind === "number" ? Number(value) : value);
    },
    numberRule(field) {
      return (value) =>
        value === "" ||
        value == null ||
        (Number.isFinite(Number(value)) &&
          Number(value) >= field.min &&
          (field.step === "any" || Number.isInteger(Number(value)))) ||
        `Use ${field.step === "any" ? "a number" : "a whole number"} of at least ${field.min}`;
    },
  },
};
</script>
