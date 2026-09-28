<template>
  <v-input
    ref="input"
    :model-value="modelValue"
    :rules="validationRules"
    :error-messages="loadError"
    class="code-input"
  >
    <div class="code-wrapper">
      <div v-show="!modelValue" class="code-placeholder">{{ placeholder }}</div>
      <div ref="editorHost" class="code-editor"></div>
    </div>
  </v-input>
</template>

<script>
import { markRaw } from "vue";
import loader from "@monaco-editor/loader";
import jsYaml from "js-yaml";
import { capitalize } from "lodash";

export default {
  name: "CodeEditor",
  emits: ["update:modelValue"],
  props: {
    modelValue: { type: String, default: "" },
    placeholder: { type: String, default: "" },
    language: { type: String, default: "text/plain" },
    rules: { type: Array, default: () => [] },
  },
  data: () => ({ editor: null, subscriptions: [], disposed: false, loadError: "", monaco: null }),
  computed: {
    validationRules() {
      return [...this.rules, this.validateSyntax];
    },
  },
  watch: {
    modelValue(value) {
      if (this.editor && value !== this.editor.getValue()) this.editor.setValue(value);
    },
    language(value) {
      if (this.editor) this.monaco.editor.setModelLanguage(this.editor.getModel(), value);
    },
  },
  async mounted() {
    try {
      const monaco = await loader.init();
      if (this.disposed) return;
      this.monaco = markRaw(monaco);
      monaco.editor.defineTheme("mc-hub", {
        base: "vs",
        inherit: true,
        colors: { "editor.background": "#f9f9f9" },
        rules: [],
      });
      this.editor = markRaw(
        monaco.editor.create(this.$refs.editorHost, {
          value: this.modelValue,
          theme: "mc-hub",
          language: this.language,
          automaticLayout: true,
          lineNumbers: "on",
          folding: false,
          glyphMargin: false,
          minimap: { enabled: false },
        })
      );
      this.subscriptions = [
        markRaw(
          this.editor.onDidChangeModelContent(() => {
            const value = this.editor.getValue();
            if (value !== this.modelValue) this.$emit("update:modelValue", value);
          })
        ),
        markRaw(this.editor.onDidBlurEditorText(() => this.validateCode())),
      ];
    } catch (error) {
      if (!this.disposed) this.loadError = "Unable to load the code editor. Reload to retry.";
    }
  },
  beforeUnmount() {
    this.disposed = true;
    for (const subscription of this.subscriptions) subscription.dispose();
    if (this.editor) {
      const model = this.editor.getModel();
      this.editor.dispose();
      model?.dispose();
    }
  },
  methods: {
    validateSyntax(value) {
      if (this.language !== "yaml") return true;
      try {
        jsYaml.load(value);
        return true;
      } catch (error) {
        return `Line ${error.mark.line + 1}, column ${error.mark.column + 1}: ${capitalize(error.reason)}.`;
      }
    },
    validateCode() {
      return this.$refs.input.validate();
    },
  },
};
</script>

<style scoped>
.code-wrapper {
  position: relative;
  width: 100%;
}
.code-editor {
  height: 300px;
}
.code-placeholder {
  color: grey;
  font-family: "Consolas", "Deja Vu Sans Mono", monospace;
  position: absolute;
  pointer-events: none;
  z-index: 1;
  user-select: none;
  white-space: pre;
  margin-left: 50px;
}
</style>
