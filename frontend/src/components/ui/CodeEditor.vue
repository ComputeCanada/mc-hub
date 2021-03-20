<template>
  <div>
    <div class="code-placeholder" v-show="showPlaceholder">{{ placeholder }}</div>
    <div ref="codeEditorWrapper" class="mb-2">
      <div class="code-editor"></div>
    </div>
    <v-messages :value="errorMessages" color="error" />
  </div>
</template>

<script>
import * as monaco from "monaco-editor/esm/vs/editor/editor.api";
import { VMessages, VInput } from "vuetify/es5";
import jsYaml from "js-yaml";
import { capitalize } from "lodash";

function CodeException(messages) {
  this.messages = messages;
}

const CODE_VALIDATORS = {
  yaml: code => {
    try {
      jsYaml.load(code);
      return true;
    } catch (e) {
      const message = `Line ${e.mark.line + 1}, column ${e.mark.column + 1}: ${capitalize(e.reason)}.`;
      throw new CodeException([message]);
    }
  }
};

export default {
  name: "CodeEditor",
  extends: VInput,
  components: {
    VMessages
  },
  props: {
    value: {
      type: String,
      default: ""
    },
    placeholder: {
      type: String,
      default: ""
    },
    language: {
      type: String,
      default: "text/plain"
    }
  },
  data() {
    return {
      editor: null,
      errorMessages: []
    };
  },
  watch: {
    value(value) {
      if (value !== this.editor.getValue()) this.editor.setValue(value);
    }
  },
  computed: {
    showPlaceholder() {
      return this.value.length === 0;
    }
  },
  mounted() {
    monaco.editor.defineTheme("mc-hub", {
      base: "vs",
      inherit: true,
      colors: {
        "editor.background": "#f9f9f9"
      },
      rules: []
    });
    this.editor = monaco.editor.create(this.$refs.codeEditorWrapper.querySelector(".code-editor"), {
      value: this.value,
      theme: "mc-hub",
      language: this.language,
      automaticLayout: true,
      lineNumbers: "on",
      folding: false,
      glyphMargin: false,
      minimap: {
        enabled: false
      }
    });
    this.editor.onDidChangeModelContent(() => {
      const code = this.editor.getValue();
      this.$emit("input", code);

      this.errorMessages = [];
    });
    this.editor.onDidBlurEditorText(() => {
      this.validateCode();
    });
  },
  methods: {
    validateCode() {
      // validate code
      try {
        CODE_VALIDATORS[this.language](this.editor.getValue());
        this.errorMessages = [];
      } catch (e) {
        this.errorMessages = e.messages;
      }
    }
  }
};
</script>

<style scoped>
.code-editor {
  height: 300px;
}

.code-placeholder {
  color: grey;
  font-family: "Consolas", "Deja Vu Sans Mono", "Bitstream Vera Sans Mono", monospace;
  position: absolute;
  pointer-events: none;
  z-index: 100;
  user-select: none;
  cursor: text;
  white-space: pre;
  margin-left: 50px;
}
</style>
