// vite.config.ts
import { fileURLToPath, URL } from "node:url";
import vue from "file:///mnt/c/workspace/vibecoding-platform/ide/terminal/butterfly-with-ai/frontend/node_modules/.pnpm/@vitejs+plugin-vue@5.2.4_vite@6.3.5_@types+node@22.15.31_sass-embedded@1.89.2__vue@3.5.16_typescript@5.8.3_/node_modules/@vitejs/plugin-vue/dist/index.mjs";
import { defineConfig } from "file:///mnt/c/workspace/vibecoding-platform/ide/terminal/butterfly-with-ai/frontend/node_modules/.pnpm/vite@6.3.5_@types+node@22.15.31_sass-embedded@1.89.2/node_modules/vite/dist/node/index.js";
import vueDevTools from "file:///mnt/c/workspace/vibecoding-platform/ide/terminal/butterfly-with-ai/frontend/node_modules/.pnpm/vite-plugin-vue-devtools@7.7.6_rollup@4.43.0_vite@6.3.5_@types+node@22.15.31_sass-embed_48e8a193d2c5c6eb3fe20b9912c6e24c/node_modules/vite-plugin-vue-devtools/dist/vite.mjs";
var __vite_injected_original_import_meta_url = "file:///mnt/c/workspace/vibecoding-platform/ide/terminal/butterfly-with-ai/frontend/vite.config.ts";
var vite_config_default = defineConfig({
  base: "./",
  // Set the base public path for assets
  plugins: [
    vue(),
    vueDevTools()
  ],
  define: {
    global: "globalThis",
    process: {
      env: {}
    }
  },
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", __vite_injected_original_import_meta_url)),
      "stream": "stream-browserify",
      "buffer": "buffer"
    }
  },
  build: {
    rollupOptions: {
      output: {
        entryFileNames: `assets/[name].[hash].js`,
        chunkFileNames: `assets/[name].[hash].js`,
        assetFileNames: `assets/[name].[hash].[ext]`
      }
    }
  },
  server: {
    watch: {
      usePolling: true
    }
  }
});
export {
  vite_config_default as default
};
//# sourceMappingURL=data:application/json;base64,ewogICJ2ZXJzaW9uIjogMywKICAic291cmNlcyI6IFsidml0ZS5jb25maWcudHMiXSwKICAic291cmNlc0NvbnRlbnQiOiBbImNvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9kaXJuYW1lID0gXCIvbW50L2Mvd29ya3NwYWNlL3ZpYmVjb2RpbmctcGxhdGZvcm0vaWRlL3Rlcm1pbmFsL2J1dHRlcmZseS13aXRoLWFpL2Zyb250ZW5kXCI7Y29uc3QgX192aXRlX2luamVjdGVkX29yaWdpbmFsX2ZpbGVuYW1lID0gXCIvbW50L2Mvd29ya3NwYWNlL3ZpYmVjb2RpbmctcGxhdGZvcm0vaWRlL3Rlcm1pbmFsL2J1dHRlcmZseS13aXRoLWFpL2Zyb250ZW5kL3ZpdGUuY29uZmlnLnRzXCI7Y29uc3QgX192aXRlX2luamVjdGVkX29yaWdpbmFsX2ltcG9ydF9tZXRhX3VybCA9IFwiZmlsZTovLy9tbnQvYy93b3Jrc3BhY2UvdmliZWNvZGluZy1wbGF0Zm9ybS9pZGUvdGVybWluYWwvYnV0dGVyZmx5LXdpdGgtYWkvZnJvbnRlbmQvdml0ZS5jb25maWcudHNcIjtpbXBvcnQgeyBmaWxlVVJMVG9QYXRoLCBVUkwgfSBmcm9tICdub2RlOnVybCdcblxuaW1wb3J0IHZ1ZSBmcm9tICdAdml0ZWpzL3BsdWdpbi12dWUnXG5pbXBvcnQgeyBkZWZpbmVDb25maWcgfSBmcm9tICd2aXRlJ1xuaW1wb3J0IHZ1ZURldlRvb2xzIGZyb20gJ3ZpdGUtcGx1Z2luLXZ1ZS1kZXZ0b29scydcblxuLy8gaHR0cHM6Ly92aXRlLmRldi9jb25maWcvXG5leHBvcnQgZGVmYXVsdCBkZWZpbmVDb25maWcoe1xuICBiYXNlOiAnLi8nLCAvLyBTZXQgdGhlIGJhc2UgcHVibGljIHBhdGggZm9yIGFzc2V0c1xuICBwbHVnaW5zOiBbXG4gICAgdnVlKCksXG4gICAgdnVlRGV2VG9vbHMoKSxcbiAgXSxcbiAgZGVmaW5lOiB7XG4gICAgZ2xvYmFsOiAnZ2xvYmFsVGhpcycsXG4gICAgcHJvY2Vzczoge1xuICAgICAgZW52OiB7fVxuICAgIH1cbiAgfSxcbiAgcmVzb2x2ZToge1xuICAgIGFsaWFzOiB7XG4gICAgICAnQCc6IGZpbGVVUkxUb1BhdGgobmV3IFVSTCgnLi9zcmMnLCBpbXBvcnQubWV0YS51cmwpKSxcbiAgICAgICdzdHJlYW0nOiAnc3RyZWFtLWJyb3dzZXJpZnknLFxuICAgICAgJ2J1ZmZlcic6ICdidWZmZXInXG4gICAgfSxcbiAgfSxcbiAgYnVpbGQ6IHtcbiAgICByb2xsdXBPcHRpb25zOiB7XG4gICAgICBvdXRwdXQ6IHtcbiAgICAgICAgZW50cnlGaWxlTmFtZXM6IGBhc3NldHMvW25hbWVdLltoYXNoXS5qc2AsXG4gICAgICAgIGNodW5rRmlsZU5hbWVzOiBgYXNzZXRzL1tuYW1lXS5baGFzaF0uanNgLFxuICAgICAgICBhc3NldEZpbGVOYW1lczogYGFzc2V0cy9bbmFtZV0uW2hhc2hdLltleHRdYFxuICAgICAgfVxuICAgIH1cbiAgfSxcbiAgc2VydmVyOiB7XG4gICAgd2F0Y2g6IHtcbiAgICAgIHVzZVBvbGxpbmc6IHRydWVcbiAgICB9XG4gIH1cbn0pXG4iXSwKICAibWFwcGluZ3MiOiAiO0FBQXNaLFNBQVMsZUFBZSxXQUFXO0FBRXpiLE9BQU8sU0FBUztBQUNoQixTQUFTLG9CQUFvQjtBQUM3QixPQUFPLGlCQUFpQjtBQUp3TyxJQUFNLDJDQUEyQztBQU9qVCxJQUFPLHNCQUFRLGFBQWE7QUFBQSxFQUMxQixNQUFNO0FBQUE7QUFBQSxFQUNOLFNBQVM7QUFBQSxJQUNQLElBQUk7QUFBQSxJQUNKLFlBQVk7QUFBQSxFQUNkO0FBQUEsRUFDQSxRQUFRO0FBQUEsSUFDTixRQUFRO0FBQUEsSUFDUixTQUFTO0FBQUEsTUFDUCxLQUFLLENBQUM7QUFBQSxJQUNSO0FBQUEsRUFDRjtBQUFBLEVBQ0EsU0FBUztBQUFBLElBQ1AsT0FBTztBQUFBLE1BQ0wsS0FBSyxjQUFjLElBQUksSUFBSSxTQUFTLHdDQUFlLENBQUM7QUFBQSxNQUNwRCxVQUFVO0FBQUEsTUFDVixVQUFVO0FBQUEsSUFDWjtBQUFBLEVBQ0Y7QUFBQSxFQUNBLE9BQU87QUFBQSxJQUNMLGVBQWU7QUFBQSxNQUNiLFFBQVE7QUFBQSxRQUNOLGdCQUFnQjtBQUFBLFFBQ2hCLGdCQUFnQjtBQUFBLFFBQ2hCLGdCQUFnQjtBQUFBLE1BQ2xCO0FBQUEsSUFDRjtBQUFBLEVBQ0Y7QUFBQSxFQUNBLFFBQVE7QUFBQSxJQUNOLE9BQU87QUFBQSxNQUNMLFlBQVk7QUFBQSxJQUNkO0FBQUEsRUFDRjtBQUNGLENBQUM7IiwKICAibmFtZXMiOiBbXQp9Cg==
