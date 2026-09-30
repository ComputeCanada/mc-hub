<template>
  <v-dialog :model-value="modelValue" @update:model-value="input" :max-width="maxWidth">
    <v-card>
      <v-card-title>
        <v-icon v-if="alert" class="mr-2" color="red">mdi-alert</v-icon>
        {{ title }}
      </v-card-title>
      <v-card-text>
        <slot></slot>
      </v-card-text>
      <v-divider></v-divider>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn color="primary" :variant="encourageConfirm ? 'elevated' : 'text'" @click="confirm">Yes</v-btn>
        <v-btn color="primary" :variant="encourageCancel ? 'elevated' : 'text'" @click="cancel">No</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
export default {
  name: "ConfirmDialog",
  emits: ["update:modelValue", "confirm", "cancel"],
  props: {
    modelValue: {
      type: Boolean,
      required: true,
    },
    title: {
      type: String,
      default: "Are you sure?",
    },
    alert: {
      type: Boolean,
      default: false,
    },
    encourageConfirm: {
      type: Boolean,
      default: false,
    },
    encourageCancel: {
      type: Boolean,
      default: false,
    },
    maxWidth: {
      type: Number,
      default: 400,
    },
  },
  methods: {
    confirm() {
      this.$emit("confirm");
      this.$emit("update:modelValue", false);
    },
    cancel() {
      this.$emit("cancel");
      this.$emit("update:modelValue", false);
    },
    input(value) {
      this.$emit("update:modelValue", value);
    },
  },
};
</script>

<style scoped></style>
