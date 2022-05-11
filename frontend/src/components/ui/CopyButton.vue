<template>
  <v-btn title="Copy to clipboard" icon small @click="copy"
    ><v-icon small :color="color">mdi-content-copy</v-icon></v-btn
  >
</template>

<script>
export default {
  name: "CopyButton",
  props: {
    color: {
      type: String,
      required: true,
    },
    text: {
      type: String,
      required: true,
    },
  },
  methods: {
    copy() {
      navigator.clipboard.writeText(this.text);
    },
  },
};
</script>

<style scoped></style>
