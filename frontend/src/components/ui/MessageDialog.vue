<template>
  <v-dialog v-model="value" max-width="400">
    <v-card>
      <v-card-title v-if="type === 'success'">Success</v-card-title>
      <v-card-title v-else>Error</v-card-title>
      <v-card-text>
        <slot></slot>
      </v-card-text>
      <v-divider></v-divider>
      <v-card-actions>
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
      required: true
    },
    type: {
      type: String,
      required: true,
      validator: value => ["error", "success"].includes(value)
    }
  },
  methods: {
    close() {
      this.$emit("input", false);
    }
  }
};
</script>

<style scoped></style>
