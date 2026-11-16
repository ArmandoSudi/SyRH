import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

const DJANGO = 'http://127.0.0.1:8000'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue(), vueDevTools()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    // The browser only ever talks to Vite; /api and /admin go to Django.
    // The object form keeps the browser's Host header (the string shorthand
    // rewrites it), so Django sees one origin and its CSRF origin check passes,
    // exactly as behind the production web server.
    proxy: Object.fromEntries(
      ['/api', '/admin', '/static'].map((path) => [path, { target: DJANGO }]),
    ),
  },
})
