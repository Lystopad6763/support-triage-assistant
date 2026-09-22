import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Relative base: the built page is served by FastAPI from wherever it sits,
// and an absolute /assets/... path breaks the moment it is not the root.
export default defineConfig({
  plugins: [react()],
  base: './',
  build: { outDir: 'dist', emptyOutDir: true },
  server: {
    // In dev the page runs on 5173 and the API on 8000; proxying keeps the
    // fetch path identical to production, so there is no "works locally" gap.
    proxy: {
      '/draft': 'http://127.0.0.1:8000',
      '/classify': 'http://127.0.0.1:8000',
      '/taxonomy': 'http://127.0.0.1:8000',
      '/health': 'http://127.0.0.1:8000',
    },
  },
})
