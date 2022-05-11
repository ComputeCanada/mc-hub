<template>
  <v-dialog :value="value" @input="input" max-width="400" :persistent="persistent">
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
        <v-btn color="primary" text @click="close">Close</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
export default {
  name: "MessageDialog",
  props: {
    value: {
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
      this.$emit("input", false);
      if (this.callback != null) {
        this.callback();
      }
    },
    input(value) {
      this.$emit("input", value);
    },
  },
};
</script>

<style scoped></style>
