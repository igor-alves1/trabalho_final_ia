import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Proxy /api e /faces para o backend stdlib (porta 8000), evitando CORS.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8000',
      '/faces': 'http://localhost:8000',
    },
  },
})
