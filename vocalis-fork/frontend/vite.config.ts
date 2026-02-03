import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  
  // Environment variable prefix (VITE_ variables are exposed to client)
  envPrefix: 'VITE_',
  
  // Build output for Cloudflare Pages
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
  
  server: {
    port: 3000,
    open: true,
    proxy: {
      // Proxy WebSocket connections to backend (dev only)
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      },
      // Proxy REST API calls to backend (dev only)
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
