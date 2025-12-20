import { createRouter, createWebHistory, type RouteRecordRaw } from "vue-router";

// 路由配置
const routes: RouteRecordRaw[] = [
  {
    path: "/",
    name: "Home",
    component: () => import("@/features/home/views/Home.vue"),
    meta: { title: "首页" },
  },
  // [New] 新增收藏路由
  {
    path: "/collections",
    name: "MyCollections",
    component: () => import("@/features/user/views/MyCollections.vue"),
    meta: { title: "我的收藏", requiresAuth: true },
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
    path: '/center/analysis/:videoId?', // 可选参数视频ID
    name: 'SmartAnalysis',
    component: () => import('@/features/video/center/views/SmartAnalysis.vue'),
    meta: { title: '智能分析', requiresAuth: true }
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
  // 管理员路由 - 必须在创建router之前添加
  {
    path: '/admin',
    component: () => import('@/features/admin/layouts/AdminLayout.vue'),
    meta: { requiresAuth: true, requiresAdmin: true },
    children: [
      {
        path: '',
        redirect: '/admin/dashboard'
      },
      {
        path: 'dashboard',
        name: 'AdminDashboard',
        component: () => import('@/features/admin/views/Dashboard.vue'),
        meta: { title: '数据中心' }
      },
      {
        path: 'audit',
        name: 'AdminAudit',
        component: () => import('@/features/admin/views/VideoAudit.vue'),
        meta: { title: '视频审核' }
      },
      {
        path: 'reports',
        name: 'AdminReports',
        component: () => import('@/features/admin/views/ReportManage.vue'),
        meta: { title: '举报处理' }
      },
      {
        path: 'users',
        name: 'AdminUsers',
        component: () => import('@/features/admin/views/UserManage.vue'),
        meta: { title: '用户管理' }
      },
      {
        path: 'categories',
        name: 'AdminCategories',
        component: () => import('@/features/admin/views/CategoryManage.vue'),
        meta: { title: '分类管理' }
      },
      {
        path: 'ai',
        name: 'AIGovernance',
        component: () => import('@/features/admin/views/AIGovernance.vue'),
        meta: { title: 'AI 进化控制台', requiresAuth: true, requiresAdmin: true }
      },
    ]
  },
];

// 创建路由实例
const router = createRouter({
  history: createWebHistory(),
  routes,
});

// 路由守卫（导航前执行）
router.beforeEach(async (to, from, next) => {
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
    
    // 检查是否需要管理员权限
    if (to.meta.requiresAdmin) {
      // 动态导入 userStore 避免循环依赖
      const { useUserStore } = await import("@/shared/stores/user");
      const userStore = useUserStore();
      
      // 如果用户信息未加载，先加载
      if (!userStore.userInfo) {
        try {
          await userStore.fetchUserInfo();
        } catch (error) {
          console.error('获取用户信息失败:', error);
        }
      }
      
      // 检查是否是管理员
      if (!userStore.isAdmin) {
        next({ name: "Home" });
        return;
      }
    }
  }

  next();
});

export default router;

