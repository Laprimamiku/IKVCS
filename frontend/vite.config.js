import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    },
    extensions: ['.mjs', '.js', '.mts', '.ts', '.jsx', '.tsx', '.json', '.vue']
  },
  css: {
    preprocessorOptions: {
      scss: {
        // 如果需要全局 SCSS 变量，可以在这里配置
        // additionalData: `@import "@/assets/styles/variables.scss";`
      }
    }
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        // 开发环境代理目标，可通过环境变量 VITE_PROXY_TARGET 覆盖
        target: process.env.VITE_PROXY_TARGET || 'http://localhost:8000',
        changeOrigin: true
      },
      // 代理 HLS 和上传静态资源，避免抢占 SPA 路由
      '/videos/hls': {
        target: process.env.VITE_PROXY_TARGET || 'http://localhost:8000',
        changeOrigin: true
      },
      '/uploads': {
        target: process.env.VITE_PROXY_TARGET || 'http://localhost:8000',
        changeOrigin: true,
        bypass(req) {
          // HTML 直刷时返回前端入口，避免 404
          if (req.headers.accept && req.headers.accept.includes('text/html')) {
            return '/index.html'
          }
        }
      }
    }
  },
  optimizeDeps: {
    include: ['vue', 'vue-router', 'pinia', 'element-plus', '@element-plus/icons-vue']
  },
  build: {
    // 代码分割优化
    rollupOptions: {
      output: {
        manualChunks: {
          'vue-vendor': ['vue', 'vue-router', 'pinia'],
          'element-plus': ['element-plus', '@element-plus/icons-vue'],
          'video-player': [
            './src/features/video/player/views/VideoPlayer.vue',
            './src/features/video/player/composables/useVideoPlayer.ts'
          ]
        }
      }
    },
    // 启用压缩
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true,
        drop_debugger: true
      }
    }
  }
})
