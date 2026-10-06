module.exports = {
  // Babel is used only by Jest; Vite handles production transforms.
  presets: [["@babel/preset-env", { targets: { node: "current" } }]],
};
