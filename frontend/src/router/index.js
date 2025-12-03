/**
 * Vue Router 路由配置
 * 
 * 这个文件定义了所有页面的路由
 * 相当于 Spring MVC 的 @RequestMapping
 */
import { createRouter, createWebHistory } from 'vue-router'

// 路由配置
const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('../views/Home.vue'),
    meta: { title: '首页' }
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/auth/Login.vue'),
    meta: { title: '登录' }
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('../views/auth/Register.vue'),
    meta: { title: '注册' }
  },
  // TODO: 后续添加更多路由
  // {
  //   path: '/videos/:id',
  //   name: 'VideoDetail',
  //   component: () => import('../views/video/VideoDetail.vue'),
  //   meta: { title: '视频详情', requiresAuth: true }
  // },
]

// 创建路由实例
const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫（导航前执行）
// 相当于 Spring Security 的权限检查
router.beforeEach((to, from, next) => {
  // 设置页面标题
  document.title = to.meta.title ? `${to.meta.title} - IKVCS` : 'IKVCS'
  
  // 检查是否需要登录
  if (to.meta.requiresAuth) {
    const token = localStorage.getItem('access_token')
    if (!token) {
      // 未登录，跳转到登录页
      next({ name: 'Login', query: { redirect: to.fullPath } })
      return
    }
  }
  
  next()
})

export default router
