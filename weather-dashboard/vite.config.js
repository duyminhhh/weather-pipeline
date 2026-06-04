import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Route Databricks API calls qua dev server để tránh CORS
      '/api/databricks': {
        target: 'https://dbc-5a58e852-eb06.cloud.databricks.com',
        changeOrigin: true,
        secure: true,
        rewrite: (path) => path.replace(/^\/api\/databricks/, ''),
        headers: {
          'Accept': 'application/json',
        },
      },
      // Route Open-Meteo API
      '/api/weather': {
        target: 'https://api.open-meteo.com',
        changeOrigin: true,
        secure: true,
        rewrite: (path) => path.replace(/^\/api\/weather/, ''),
      },
    },
  },
})
