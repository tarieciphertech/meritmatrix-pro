import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      // Proxy API requests to the FastAPI backend during development.
      // The backend expects requests at /api/v1 and CORS is configured
      // for http://localhost:5173, but proxying keeps the frontend
      // same-origin and avoids CORS entirely in dev.
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
