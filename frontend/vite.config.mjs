import { fileURLToPath, URL } from 'node:url'
import vue from '@vitejs/plugin-vue'
// import jsconfigPaths from 'vite-jsconfig-paths'

// https://vitejs.dev/config/
export default {
  plugins: [vue()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://backend:8000',
        rewrite: (path) => path.replace(/^\/api/, ''),
        changeOrigin: true,
        secure: false,
      }
    }
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  }
}