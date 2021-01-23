<template>
  <span>
    <code>{{ visible ? password : "**********" }}</code>
    <v-btn icon small style="margin: -6px 0;" @click="visible = !visible">
      <v-icon small :color="color">{{ visible ? "mdi-eye-off" : "mdi-eye" }}</v-icon>
    </v-btn>
  </span>
</template>

<script>
export default {
  name: "PasswordDisplay",
  props: {
    password: {
      required: true,
      type: String
    },
    color: {
      required: true,
      type: String
    }
  },
  data() {
    return {
      visible: false
    };
  }
};
</script>
