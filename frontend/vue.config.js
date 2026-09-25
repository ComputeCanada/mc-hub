const MonacoWebpackPlugin = require("monaco-editor-webpack-plugin");
const foundation = process.env.MC_HUB_VUE3_FOUNDATION === "true";

module.exports = {
  ...(foundation && {
    outputDir: "dist/vue3-foundation",
    pages: {
      index: {
        entry: "src/foundation/main.js",
        template: "public/index.html",
        title: "MC Hub Vue 3 foundation",
      },
    },
  }),
  transpileDependencies: ["vuetify"],
  chainWebpack: (config) => {
    config.plugin("monaco-editor").use(MonacoWebpackPlugin, [
      {
        // Languages are loaded on demand at runtime
        languages: ["yaml"],
      },
    ]);
  },
};
