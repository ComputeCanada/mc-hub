<template>
  <div>
    <div class="code-placeholder" v-show="showPlaceholder">{{ placeholder }}</div>
    <div ref="codeEditorWrapper">
      <div class="code-editor"></div>
    </div>
  </div>
</template>

<script>
import * as monaco from "monaco-editor/esm/vs/editor/editor.api";

export default {
  name: "CodeEditor",
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
      editor: null
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
      lineNumbers: "off",
      folding: false,
      layoutInfo: {
        height: 10
      },
      lineDecorationsWidth: 0,
      glyphMargin: false,
      minimap: {
        enabled: false
      }
    });
    this.editor.onDidChangeModelContent(() => {
      this.$emit("input", this.editor.getValue());
    });
  }
};
</script>

<style scoped>
.code-editor {
  height: 200px;
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
}
</style>
