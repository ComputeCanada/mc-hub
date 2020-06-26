<template>
  <div style="width:100%">
    <v-radio-group v-model="mode" row>
      <v-radio value="plaintext" label="Paste public key"></v-radio>
      <v-radio value="file" label="Upload public key file"></v-radio>
    </v-radio-group>
    <v-textarea
      v-show="mode == 'plaintext'"
      placeholder="ssh-rsa ..."
      :value="value"
      @change="textAreaUpdated"
      outlined
    />
    <v-file-input
      v-show="mode == 'file'"
      @change="fileInputUpdated"
      label="SSH public key file"
      outlined
    />
  </div>
</template>
<script>
export default {
  name: "PublicKeyInput",
  props: {
    value: {
      type: String,
      required: true
    }
  },
  data() {
    return {
      mode: "plaintext",
      fileReader: null
    };
  },
  created() {
    this.fileReader = new FileReader();
    this.fileReader.addEventListener("load", event => {
      this.$emit("input", this.sanitizePublicKey(event.target.result));
    });
  },
  methods: {
    textAreaUpdated(text) {
      this.$emit("input", this.sanitizePublicKey(text));
    },
    fileInputUpdated(file) {
      if (typeof file === "object") this.fileReader.readAsText(file);
      else this.$emit("input", "");
    },
    sanitizePublicKey(publicKey) {
      // The new lines (\n) at the end of ssh key files must be removed
      return publicKey.replace(/(\n)+$/, "");
    }
  }
};
</script>