import { createRouter, createWebHistory, type RouteRecordRaw } from "vue-router";

// 路由配置
const routes: RouteRecordRaw[] = [
  {
    path: "/",
    name: "Home",
    component: () => import("@/features/home/views/Home.vue"),
    meta: { title: "首页" },
  },
  {
    path: "/profile",
    name: "Profile",
    component: () => import("@/features/user/views/Profile.vue"),
    meta: { title: "个人中心", requiresAuth: true },
  },
  {
    path: "/upload",
    name: "VideoUpload",
    component: () => import("@/features/video/upload/views/VideoUpload.vue"),
    meta: { title: "上传视频", requiresAuth: true },
  },
  {
    path: "/video-center",
    name: "VideoCenter",
    component: () => import("@/features/video/center/views/VideoCenter.vue"),
    meta: { title: "视频中心", requiresAuth: true },
  },
  {
    path: "/search",
    name: "Search",
    component: () => import("@/features/search/views/Search.vue"),
    meta: { title: "搜索" },
  },
  {
    path: "/videos/:id",
    name: "VideoPlayer",
    component: () => import("@/features/video/player/views/VideoPlayer.vue"),
    meta: {
      title: "视频播放",
    },
  },
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

