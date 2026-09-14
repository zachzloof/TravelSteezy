import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

const BACKEND = 'http://localhost:8000'

// Three of these prefixes are BOTH an API prefix and a client-side route:
// /chat, /memory and /admin. Proxying them wholesale meant that typing
// localhost:5173/memory, or just reloading the page while on it, sent the
// browser's navigation to FastAPI, which answered with its own copy of the
// built index.html - referencing whatever asset hashes were in dist/ at the
// time. In a dev session those are stale, so the page 404'd its own bundle and
// rendered blank.
//
// A navigation request is distinguishable from an API call: browsers send
// Accept: text/html for one and not the other (the app's fetch() calls send
// application/json). So navigations are handed back to Vite, and everything
// else goes to the backend.
function api(prefix) {
  return {
    [prefix]: {
      target: BACKEND,
      changeOrigin: true,
      bypass(req) {
        if (req.method === 'GET' && (req.headers.accept || '').includes('text/html')) {
          return '/index.html'
        }
      }
    }
  }
}

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    // Local dev only. In production the FastAPI app serves the built frontend
    // from the same origin, so no proxy and no API base URL is involved.
    proxy: {
      ...api('/auth'),
      ...api('/admin'),
      ...api('/profile'),
      ...api('/chat'),
      ...api('/health'),
      ...api('/travel'),
      ...api('/memory'),
      ...api('/bugs')
    }
  },
  build: { outDir: 'dist', emptyOutDir: true }
})
