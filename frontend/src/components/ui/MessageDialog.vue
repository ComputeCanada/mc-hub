<template>
  <v-dialog :model-value="modelValue" @update:model-value="input" max-width="400" :persistent="persistent">
    <v-card :loading="loading">
      <v-card-title v-if="type === 'success'">Success</v-card-title>
      <v-card-title v-else-if="type === 'loading'">Loading</v-card-title>
      <v-card-title v-else>Error</v-card-title>
      <v-card-text>
        <slot></slot>
      </v-card-text>
      <v-divider></v-divider>
      <v-card-actions v-if="!noClose">
        <v-spacer></v-spacer>
        <v-btn color="primary" variant="text" @click="close">Close</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
export default {
  name: "MessageDialog",
  emits: ["update:modelValue"],
  props: {
    modelValue: {
      type: Boolean,
      required: true,
    },
    type: {
      type: String,
      required: true,
      validator: (value) => ["error", "success", "loading"].includes(value),
    },
    persistent: {
      type: Boolean,
      default: false,
    },
    noClose: {
      type: Boolean,
      default: false,
    },
    callback: Function,
  },
  computed: {
    loading() {
      return this.type === "loading";
    },
  },
  methods: {
    close() {
      this.$emit("update:modelValue", false);
      if (this.callback != null) {
        this.callback();
      }
    },
    input(value) {
      this.$emit("update:modelValue", value);
    },
  },
};
</script>

<style scoped></style>
