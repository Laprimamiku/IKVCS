/**
 * Vue 应用入口文件
 * 
 * 这个文件是整个前端应用的入口
 * 相当于 Java 的 main() 方法
 */
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

import App from "./App.vue"
import router from '@/shared/router'
import '@/shared/assets/styles/variables.scss'

// 创建 Vue 应用实例
const app = createApp(App)

// 注册 Pinia（状态管理）
app.use(createPinia())

// 注册 Vue Router（路由）
app.use(router)

// 注册 Element Plus（UI 组件库）
app.use(ElementPlus)

// 注册 Element Plus（UI 组件库）
app.use(ElementPlus, {
  // 配置 Message 组件
  message: {
    max: 3,  // 最多同时显示 3 个提示
    offset: 20,  // 距离顶部的偏移量（像素）
  },
  // 配置全局 z-index
  zIndex: 2000,  // 降低 z-index，避免遮挡重要按钮
})

// 注册 Element Plus 图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

// 挂载应用
app.mount('#app')

console.log('✅ IKVCS 前端应用启动成功')
