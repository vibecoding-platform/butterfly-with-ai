import { fileURLToPath, URL } from 'node:url'

import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'
import vueDevTools from 'vite-plugin-vue-devtools'

// https://vite.dev/config/
export default defineConfig({
  base: './', // Set the base public path for assets
  plugins: [
    vue(),
    vueDevTools(),
  ],
  define: {
    global: 'globalThis',
    process: {
      env: {}
    }
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
      'stream': 'stream-browserify',
      'buffer': 'buffer',
      'events': 'events',
      'util': 'util'
    },
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
    port: 5173,
    strictPort: true,
    watch: {
      usePolling: true
    }
  }
})
