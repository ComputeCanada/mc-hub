module.exports = {
  preset: "@vue/cli-plugin-unit-jest",
  setupFiles: ["<rootDir>/tests/setup.js"],
  // Jest 27's resolver needs explicit mappings for Vuetify's subpath exports.
  moduleNameMapper: {
    "^@/(.*)$": "<rootDir>/src/$1",
    "^vuetify/components/(.*)$": "<rootDir>/node_modules/vuetify/lib/components/$1/index.js",
    "^vuetify/directives/(.*)$": "<rootDir>/node_modules/vuetify/lib/directives/$1/index.js",
    "^vuetify/iconsets/(.*)$": "<rootDir>/node_modules/vuetify/lib/iconsets/$1.js",
  },
  transformIgnorePatterns: ["/node_modules/(?!(?:monaco-editor)|(?:vuetify)).+\\.js$"],
};
