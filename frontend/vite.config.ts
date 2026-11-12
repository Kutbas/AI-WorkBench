import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      // 开发模式统一走代理（同源，cookie/token 均无跨域问题）
      '/api': 'http://127.0.0.1:8000',
    },
  },
})
