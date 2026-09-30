module.exports = {
  testEnvironment: "jsdom",
  testEnvironmentOptions: { customExportConditions: ["node", "node-addons"] },
  moduleFileExtensions: ["js", "json", "vue"],
  testMatch: ["<rootDir>/tests/unit/**/*.spec.js"],
  transform: {
    "^.+\\.vue$": "@vue/vue3-jest",
    "^.+\\.js$": "babel-jest",
  },
  setupFiles: ["<rootDir>/tests/setup.js"],
  // Explicit ESM mappings let Babel transform Vuetify for Jest's CJS runtime.
  moduleNameMapper: {
    "\\.(css|scss|sass)$": "<rootDir>/tests/styleMock.js",
    "^@/(.*)$": "<rootDir>/src/$1",
    "^vuetify/components$": "<rootDir>/node_modules/vuetify/lib/components/index.js",
    "^vuetify/styles$": "<rootDir>/tests/styleMock.js",
    "^vuetify/components/(.*)$": "<rootDir>/node_modules/vuetify/lib/components/$1/index.js",
    "^vuetify/directives/(.*)$": "<rootDir>/node_modules/vuetify/lib/directives/$1/index.js",
    "^vuetify/iconsets/(.*)$": "<rootDir>/node_modules/vuetify/lib/iconsets/$1.js",
  },
  transformIgnorePatterns: ["/node_modules/(?!(?:monaco-editor)|(?:vuetify)).+\\.js$"],
};
