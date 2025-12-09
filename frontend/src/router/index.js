/**
 * Vue Router 路由配置
 *
 * 这个文件定义了所有页面的路由
 * 相当于 Spring MVC 的 @RequestMapping
 */
import { createRouter, createWebHistory } from "vue-router";

// 路由配置
const routes = [
  {
    path: "/",
    name: "Home",
    component: () => import("../views/Home.vue"),
    meta: { title: "首页" },
  },
  {
    path: "/profile",
    name: "Profile",
    component: () => import("../views/user/Profile.vue"),
    meta: { title: "个人中心", requiresAuth: true },
  },
  {
    path: "/upload",
    name: "VideoUpload",
    component: () => import("../views/VideoUpload.vue"),
    meta: { title: "上传视频", requiresAuth: true },
  },
  {
    path: "/video-center",
    name: "VideoCenter",
    component: () => import("../views/VideoCenter.vue"),
    meta: { title: "视频中心", requiresAuth: true },
  },
  {
    path: "/search",
    name: "Search",
    component: () => import("../views/Search.vue"),
    meta: { title: "搜索" },
  },
  {
    path: "/videos/:id",
    name: "VideoPlayer",
    component: () => import("@/views/VideoPlayer.vue"),
    meta: {
      title: "视频播放",
    },
  },

  // TODO: 后续添加更多路由
  // {
  //   path: '/videos/:id',
  //   name: 'VideoDetail',
  //   component: () => import('../views/video/VideoDetail.vue'),
  //   meta: { title: '视频详情', requiresAuth: true }
  // },
];

// 创建路由实例
const router = createRouter({
  history: createWebHistory(),
  routes,
});

// 路由守卫（导航前执行）
router.beforeEach((to, from, next) => {
  // 设置页面标题
  document.title = to.meta.title ? `${to.meta.title} - IKVCS` : "IKVCS";

  // 检查是否需要登录
  if (to.meta.requiresAuth) {
    const token = localStorage.getItem("access_token");
    if (!token) {
      // 未登录，跳转到首页（会显示登录弹窗）
      next({ name: "Home" });
      return;
    }
  }

  next();
});

export default router;
