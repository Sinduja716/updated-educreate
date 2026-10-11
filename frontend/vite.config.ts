import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // The frontend only talks to /api; the backend (FastAPI) runs on port 8000.
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
    },
  },
})
