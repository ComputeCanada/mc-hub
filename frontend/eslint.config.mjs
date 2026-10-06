import js from "@eslint/js";
import vue from "eslint-plugin-vue";
import prettier from "eslint-config-prettier";
import globals from "globals";

export default [
  { ignores: ["dist/**", "coverage/**", "test-results/**", "playwright-report/**"] },
  js.configs.recommended,
  ...vue.configs["flat/essential"],
  prettier,
  {
    files: ["**/*.{js,mjs,cjs,vue}"],
    languageOptions: { globals: { ...globals.browser, ...globals.node } },
    rules: {
      "no-unused-vars": ["error", { caughtErrors: "none" }],
      "no-console": "warn",
      "no-debugger": "warn",
    },
  },
  {
    files: ["tests/**/*.{js,cjs}"],
    languageOptions: { globals: globals.jest },
    rules: { "no-console": "off" },
  },
  { files: ["src/views/**/*.vue"], rules: { "vue/multi-word-component-names": "off" } },
];
