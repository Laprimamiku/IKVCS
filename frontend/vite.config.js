import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue({
      // Enable reactive transform for better performance
      reactivityTransform: true,
    }),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    },
    extensions: ['.mjs', '.js', '.mts', '.ts', '.jsx', '.tsx', '.json', '.vue']
  },
  css: {
    preprocessorOptions: {
      scss: {
        // Global SCSS variables are imported via index.scss
        // additionalData removed to prevent circular imports
      }
    },
    // CSS code splitting
    devSourcemap: true,
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: process.env.VITE_PROXY_TARGET || 'http://localhost:8000',
        changeOrigin: true
      },
      // 注意：不要代理 /videos，因为这是前端路由
      // 只代理 /api/v1/videos 的 API 请求
      // '/videos': {
      //   target: process.env.VITE_PROXY_TARGET || 'http://localhost:8000',
      //   changeOrigin: true
      // },
      '/uploads': {
        target: process.env.VITE_PROXY_TARGET || 'http://localhost:8000',
        changeOrigin: true,
        bypass(req) {
          if (req.headers.accept && req.headers.accept.includes('text/html')) {
            return '/index.html'
          }
        }
      }
    }
  },
  // Pre-bundle dependencies for faster dev startup
  optimizeDeps: {
    include: [
      'vue', 
      'vue-router', 
      'pinia', 
      'element-plus', 
      '@element-plus/icons-vue',
      'axios',
      'hls.js'
    ],
    // Exclude large dependencies that don't need pre-bundling
    exclude: ['@vueuse/core']
  },
  build: {
    // Target modern browsers for smaller bundle
    target: 'es2020',
    // Chunk size warning limit
    chunkSizeWarningLimit: 1000,
    // CSS code splitting
    cssCodeSplit: true,
    // Source maps for production (disable for smaller build)
    sourcemap: false,
    // Rollup options for code splitting
    rollupOptions: {
      output: {
        // Manual chunks for better caching
        manualChunks: {
          // Vue core libraries
          'vue-vendor': ['vue', 'vue-router', 'pinia'],
          // Element Plus UI library
          'element-plus': ['element-plus'],
          'element-icons': ['@element-plus/icons-vue'],
          // Video player related
          'video-libs': ['hls.js'],
          // Utility libraries
          'utils': ['axios', 'dayjs'],
        },
        // Asset file naming for better caching
        chunkFileNames: 'assets/js/[name]-[hash].js',
        entryFileNames: 'assets/js/[name]-[hash].js',
        assetFileNames: (assetInfo) => {
          const info = assetInfo.name.split('.')
          const ext = info[info.length - 1]
          if (/\.(png|jpe?g|gif|svg|webp|ico)$/.test(assetInfo.name)) {
            return 'assets/images/[name]-[hash][extname]'
          }
          if (/\.(woff2?|eot|ttf|otf)$/.test(assetInfo.name)) {
            return 'assets/fonts/[name]-[hash][extname]'
          }
          if (/\.css$/.test(assetInfo.name)) {
            return 'assets/css/[name]-[hash][extname]'
          }
          return 'assets/[name]-[hash][extname]'
        }
      },
      // Tree shaking for smaller bundle
      treeshake: {
        moduleSideEffects: 'no-external',
        propertyReadSideEffects: false,
      }
    },
    // Minification options
    minify: 'terser',
    terserOptions: {
      compress: {
        // Remove console.log in production
        drop_console: true,
        drop_debugger: true,
        // Pure function annotations for better tree shaking
        pure_funcs: ['console.log', 'console.info', 'console.debug'],
      },
      mangle: {
        // Mangle property names for smaller bundle
        properties: false,
      },
      format: {
        // Remove comments
        comments: false,
      }
    },
    // Report compressed size
    reportCompressedSize: true,
  },
  // Preview server options
  preview: {
    port: 4173,
    strictPort: true,
  },
  // Define global constants
  define: {
    __VUE_OPTIONS_API__: true,
    __VUE_PROD_DEVTOOLS__: false,
  }
})
