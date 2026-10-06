<template>
  <div style="width: 100%">
    <v-radio-group v-model="mode" inline>
      <v-radio value="plaintext" label="Paste public keys"></v-radio>
      <v-radio value="file" label="Upload public key files"></v-radio>
    </v-radio-group>
    <div v-show="mode === 'plaintext'">
      <div class="text-medium-emphasis">Enter the SSH public keys you want to authorize (one per line).</div>
      <v-textarea
        :placeholder="`ssh-rsa key1\nssh-rsa key2`"
        :model-value="keyText"
        :rules="rules"
        @update:model-value="textAreaUpdated"
        variant="outlined"
      />
    </div>
    <div v-show="mode === 'file'">
      <v-file-input
        @update:model-value="fileInputUpdated"
        multiple
        label="SSH public key files"
        :rules="rules"
        variant="outlined"
      />
    </div>
  </div>
</template>
<script>
export default {
  name: "PublicKeyInput",
  emits: ["update:modelValue"],
  props: {
    modelValue: {
      type: Array,
      required: true,
    },
    rules: {
      type: Array,
      default: () => [true],
    },
  },
  data() {
    return {
      mode: "plaintext",
      keyText: this.modelValue.join("\n"),
    };
  },
  watch: {
    modelValue: {
      deep: true,
      handler(value) {
        // Keep a trailing newline while typing the next key. Only replace the
        // draft when the parent supplies a different normalized key list.
        const draft = this.sanitizePublicKeys(this.keyText.split("\n"));
        if (JSON.stringify(draft) !== JSON.stringify(value)) this.keyText = value.join("\n");
      },
    },
  },
  methods: {
    textAreaUpdated(text) {
      this.keyText = text || "";
      const publicKeys = this.keyText.split("\n");
      this.$emit("update:modelValue", this.sanitizePublicKeys(publicKeys));
    },
    async fileInputUpdated(files) {
      const readTextFile = (file) => {
        return new Promise((resolve, reject) => {
          let fileReader = new FileReader();
          fileReader.onload = (event) => resolve(event.target.result);
          fileReader.onerror = reject;
          fileReader.readAsText(file);
        });
      };

      const publicKeys = await Promise.all((files || []).map((file) => readTextFile(file)));
      this.$emit("update:modelValue", this.sanitizePublicKeys(publicKeys));
    },
    sanitizePublicKeys(publicKeys) {
      // The new lines (\n) at the end of ssh key must be removed
      let sanitizedPublicKeys = publicKeys
        .map((publicKey) => publicKey.replace(/([\n\r])+$/, ""))
        .filter((publicKey) => publicKey !== "");
      if (sanitizedPublicKeys.length === 0) {
        return [];
      } else {
        return sanitizedPublicKeys;
      }
    },
  },
};
</script>
