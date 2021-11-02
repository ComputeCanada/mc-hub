<template>
  <div style="width:100%">
    <v-radio-group v-model="mode" row>
      <v-radio value="plaintext" label="Paste public keys"></v-radio>
      <v-radio value="file" label="Upload public key files"></v-radio>
    </v-radio-group>
    <div v-show="mode === 'plaintext'">
      <div class="text--secondary">
        Enter the SSH public keys you want to authorize (one per line).
      </div>
      <v-textarea
        :placeholder="`ssh-rsa key1\nssh-rsa key2`"
        :value="readableKeys"
        :rules="rules"
        @change="textAreaUpdated"
        outlined
      />
    </div>
    <div v-show="mode === 'file'">
      <v-file-input @change="fileInputUpdated" multiple label="SSH public key files" :rules="rules" outlined />
    </div>
  </div>
</template>
<script>
export default {
  name: "PublicKeyInput",
  props: {
    value: {
      type: Array,
      required: true
    },
    rules: {
      type: Array,
      default: () => [true]
    }
  },
  data() {
    return {
      mode: "plaintext"
    };
  },
  computed: {
    readableKeys() {
      return this.value.join("\n");
    }
  },
  methods: {
    textAreaUpdated(text) {
      const publicKeys = text.split("\n");
      this.$emit("input", this.sanitizePublicKeys(publicKeys));
    },
    async fileInputUpdated(files) {
      const readTextFile = file => {
        return new Promise((resolve, reject) => {
          let fileReader = new FileReader();
          fileReader.onload = event => resolve(event.target.result);
          fileReader.onerror = reject;
          fileReader.readAsText(file);
        });
      };

      const publicKeys = await Promise.all(files.map(file => readTextFile(file)));
      this.$emit("input", this.sanitizePublicKeys(publicKeys));
    },
    sanitizePublicKeys(publicKeys) {
      // The new lines (\n) at the end of ssh key must be removed
      let sanitizedPublicKeys = publicKeys
        .map(publicKey => publicKey.replace(/([\n\r])+$/, ""))
        .filter(publicKey => publicKey !== "");
      if (sanitizedPublicKeys.length === 0) {
        return [];
      } else {
        return sanitizedPublicKeys;
      }
    }
  }
};
</script>
