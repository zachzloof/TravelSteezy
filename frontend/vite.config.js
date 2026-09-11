import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    // Local dev only. In production the FastAPI app serves the built frontend
    // from the same origin, so no proxy and no API base URL is involved.
    proxy: {
      '/auth': 'http://localhost:8000',
      '/admin': 'http://localhost:8000',
      '/profile': 'http://localhost:8000',
      '/chat': 'http://localhost:8000',
      '/health': 'http://localhost:8000'
    }
  },
  build: { outDir: 'dist', emptyOutDir: true }
})
