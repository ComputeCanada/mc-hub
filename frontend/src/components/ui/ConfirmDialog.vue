<template>
  <v-dialog :value="value" @input="input" :max-width="maxWidth">
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
        <v-btn color="primary" :text="!encourageConfirm" @click="confirm">Yes</v-btn>
        <v-btn color="primary" :text="!encourageCancel" @click="cancel">No</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
export default {
  name: "ConfirmDialog",
  props: {
    value: {
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
      this.$emit("input", false);
    },
    cancel() {
      this.$emit("cancel");
      this.$emit("input", false);
    },
    input(value) {
      this.$emit("input", value);
    },
  },
};
</script>

<style scoped></style>
