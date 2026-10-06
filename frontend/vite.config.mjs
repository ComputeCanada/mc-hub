import { fileURLToPath, URL } from "node:url";
import { defineConfig, loadEnv } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), ["VITE_", "VUE_APP_"]);
  return {
    plugins: [vue()],
    resolve: {
      alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
      extensions: [".mjs", ".js", ".ts", ".jsx", ".tsx", ".json", ".vue"],
    },
    // Preserve existing deployments' API override; expose only this public value.
    define: {
      "process.env.BASE_URL": JSON.stringify("/"),
      "process.env.VUE_APP_API_URL": JSON.stringify(env.VITE_API_URL || env.VUE_APP_API_URL || "/api"),
    },
    server: {
      port: 8080,
      strictPort: true,
      proxy: { "/api": { target: env.VITE_API_PROXY_TARGET || "http://127.0.0.1:5000" } },
    },
    build: {
      // Flask already serves /js and /css, including lazy-loaded route chunks.
      rolldownOptions: {
        output: {
          entryFileNames: "js/[name]-[hash].js",
          chunkFileNames: "js/[name]-[hash].js",
          assetFileNames: (asset) =>
            asset.names.some((name) => name.endsWith(".css")) ? "css/[name]-[hash][extname]" : "js/[name]-[hash][extname]",
        },
      },
    },
  };
});
