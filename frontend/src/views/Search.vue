<template>
  <div class="search-page">
    <!-- 顶部导航栏（复用Home的header） -->
    <header class="app-header">
      <div class="header-wrapper">
        <!-- Logo -->
        <div class="logo" @click="router.push('/')">
          <svg class="logo-icon" viewBox="0 0 24 24" fill="currentColor">
            <path
              d="M17.813 4.653h.854c1.51.054 2.769.578 3.773 1.574 1.004.995 1.524 2.249 1.56 3.76v7.36c-.036 1.51-.556 2.769-1.56 3.773s-2.262 1.524-3.773 1.56H5.333c-1.51-.036-2.769-.556-3.773-1.56S.036 18.858 0 17.347v-7.36c.036-1.511.556-2.765 1.56-3.76 1.004-.996 2.262-1.52 3.773-1.574h.774l-1.174-1.12a1.234 1.234 0 0 1-.373-.906c0-.356.124-.658.373-.907l.027-.027c.267-.249.573-.373.92-.373.347 0 .653.124.92.373L9.653 4.44c.071.071.134.142.187.213h4.267a.836.836 0 0 1 .16-.213l2.853-2.747c.267-.249.573-.373.92-.373.347 0 .662.151.929.4.267.249.391.551.391.907 0 .355-.124.657-.373.906zM5.333 7.24c-.746.018-1.373.276-1.88.773-.506.498-.769 1.13-.786 1.894v7.52c.017.764.28 1.395.786 1.893.507.498 1.134.756 1.88.773h13.334c.746-.017 1.373-.275 1.88-.773.506-.498.769-1.129.786-1.893v-7.52c-.017-.765-.28-1.396-.786-1.894-.507-.497-1.134-.755-1.88-.773zM8 11.107c.373 0 .684.124.933.373.25.249.383.569.4.96v1.173c-.017.391-.15.711-.4.96-.249.25-.56.374-.933.374s-.684-.125-.933-.374c-.25-.249-.383-.569-.4-.96V12.44c0-.373.129-.689.386-.947.258-.257.574-.386.947-.386zm8 0c.373 0 .684.124.933.373.25.249.383.569.4.96v1.173c-.017.391-.15.711-.4.96-.249.25-.56.374-.933.374s-.684-.125-.933-.374c-.25-.249-.383-.569-.4-.96V12.44c.017-.391.15-.711.4-.96.249-.249.56-.373.933-.373Z"
            />
          </svg>
          <span class="logo-text">IKVCS</span>
        </div>

        <!-- 搜索框 -->
        <div class="search-box">
          <input
            v-model="searchKeyword"
            type="text"
            class="search-input"
            placeholder="搜索视频、UP主..."
            @keyup.enter="handleSearch"
          />
          <button class="search-btn" @click="handleSearch">
            <el-icon><Search /></el-icon>
          </button>
        </div>

        <!-- 右侧用户区 -->
        <div class="user-actions">
          <template v-if="userStore.isLoggedIn">
            <el-button
              type="primary"
              size="small"
              class="upload-btn"
              @click="router.push('/upload')"
            >
              <el-icon><Upload /></el-icon>
              上传视频
            </el-button>
            <el-dropdown trigger="click" @command="handleCommand">
              <div class="user-info">
                <el-avatar :src="userStore.avatar" :size="32" />
                <span class="user-name">{{ userStore.nickname }}</span>
                <el-icon><ArrowDown /></el-icon>
              </div>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="profile">
                    <el-icon><User /></el-icon> 个人中心
                  </el-dropdown-item>
                  <el-dropdown-item divided command="logout">
                    <el-icon><SwitchButton /></el-icon> 退出登录
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
          <template v-else>
            <el-button
              type="primary"
              size="small"
              @click="showAuthDialog('login')"
            >
              登录
            </el-button>
            <el-button
              type="primary"
              plain
              size="small"
              @click="showAuthDialog('register')"
            >
              注册
            </el-button>
          </template>
        </div>
      </div>
    </header>

    <!-- 主内容区 -->
    <main class="main-content">
      <div class="content-container">
        <!-- 搜索信息栏 -->
        <div class="search-info">
          <h2 class="search-title">
            <template v-if="currentKeyword">
              搜索结果：<span class="keyword">{{ currentKeyword }}</span>
            </template>
            <template v-else> 全部视频 </template>
          </h2>
          <div class="search-meta">
            <span v-if="total > 0">找到 {{ total }} 个结果</span>
            <span v-else>暂无结果</span>
          </div>
        </div>

        <!-- 分类筛选 -->
        <div class="filter-bar">
          <div class="filter-section">
            <span class="filter-label">分类：</span>
            <div class="filter-options">
              <span
                class="filter-option"
                :class="{ 'is-active': currentCategory === null }"
                @click="selectCategory(null)"
              >
                全部
              </span>
              <span
                v-for="cat in categories"
                :key="cat.id"
                class="filter-option"
                :class="{ 'is-active': currentCategory === cat.id }"
                @click="selectCategory(cat.id)"
              >
                {{ cat.name }}
              </span>
            </div>
          </div>
        </div>

        <!-- 视频列表 -->
        <VideoGrid
          :videos="videos"
          :loading="loading"
          :has-more="hasMore"
          @load-more="loadMoreVideos"
          @video-click="handleVideoClick"
          @watch-later="handleWatchLater"
        />
      </div>
    </main>

    <!-- 登录注册弹窗 -->
    <AuthDialog
      v-model="authDialogVisible"
      :mode="authMode"
      @success="handleAuthSuccess"
    />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch } from "vue";
import { useRouter, useRoute } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  Search,
  User,
  ArrowDown,
  SwitchButton,
  Upload,
} from "@element-plus/icons-vue";
import { useUserStore } from "@/stores/user";
import { getVideoList } from "@/api/video";
import { getCategories } from "@/api/category";
import AuthDialog from "@/components/AuthDialog.vue";
import VideoGrid from "@/components/video/VideoGrid.vue";

const router = useRouter();
const route = useRoute();
const userStore = useUserStore();

// 静态资源基址（用于拼接封面、头像等相对路径）
const resolveFileUrl = (path) => {
  if (!path) return "";
  if (path.startsWith("http")) return path;
  const base =
    import.meta.env.VITE_FILE_BASE_URL ||
    (import.meta.env.VITE_API_BASE_URL
      ? import.meta.env.VITE_API_BASE_URL.replace(/\/api\/v1$/, "")
      : window.location.origin);
  return `${base}${path}`;
};

// 搜索相关
const searchKeyword = ref("");
const currentKeyword = ref("");

// 分类相关
const currentCategory = ref(null);
const categories = ref([]);

// 视频数据
const videos = ref([]);
const loading = ref(false);
const total = ref(0);
const currentPage = ref(1);
const pageSize = ref(20);
const hasMore = ref(true);

// 认证弹窗
const authDialogVisible = ref(false);
const authMode = ref("login");

/**
 * 初始化
 */
onMounted(async () => {
  // 从URL获取搜索关键词
  if (route.query.keyword) {
    searchKeyword.value = route.query.keyword;
    currentKeyword.value = route.query.keyword;
  }

  // 从URL获取分类
  if (route.query.category_id) {
    currentCategory.value = parseInt(route.query.category_id);
  }

  // 加载分类列表
  await loadCategories();

  // 加载视频列表
  await loadVideos();
});

/**
 * 监听路由变化
 */
watch(
  () => route.query,
  (newQuery) => {
    if (
      newQuery.keyword !== currentKeyword.value ||
      newQuery.category_id !== currentCategory.value?.toString()
    ) {
      searchKeyword.value = newQuery.keyword || "";
      currentKeyword.value = newQuery.keyword || "";
      currentCategory.value = newQuery.category_id
        ? parseInt(newQuery.category_id)
        : null;
      currentPage.value = 1;
      loadVideos();
    }
  }
);

/**
 * 加载分类列表
 */
const loadCategories = async () => {
  try {
    const response = await getCategories();

    // 处理两种响应格式：
    // 1. 被拦截器包装后的格式：{ success: true, data: [...] }
    // 2. 直接返回数组的格式：[...]
    if (response && response.data && Array.isArray(response.data)) {
      categories.value = response.data;
    } else if (Array.isArray(response)) {
      categories.value = response;
    } else {
      categories.value = [];
    }
  } catch (error) {
    console.error("加载分类失败:", error);
    categories.value = [];
  }
};

/**
 * 加载视频列表
 */
const loadVideos = async (append = false) => {
  if (loading.value) return;

  loading.value = true;

  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value,
    };

    // 添加搜索关键词
    if (currentKeyword.value) {
      params.keyword = currentKeyword.value;
    }

    // 添加分类筛选
    if (currentCategory.value) {
      params.category_id = currentCategory.value;
    }

    const response = await getVideoList(params);

    if (response.success) {
      const newVideos = (response.data.items || []).map((video) => ({
        id: video.id,
        title: video.title,
        cover: resolveFileUrl(video.cover_url),
        duration: formatDuration(video.duration),
        views: video.view_count,
        likes: video.like_count || 0,
        danmaku: video.danmaku_count || 0,
        author: {
          name:
            video.uploader?.nickname || video.uploader?.username || "未知用户",
          avatar: resolveFileUrl(video.uploader?.avatar || ""),
          verified: false,
          verifiedType: "personal",
        },
        tags: [],
        publishTime: video.created_at,
      }));

      if (append) {
        videos.value.push(...newVideos);
      } else {
        videos.value = newVideos;
      }

      total.value = response.data.total || 0;
      hasMore.value = videos.value.length < total.value;
    }
  } catch (error) {
    console.error("加载视频列表失败:", error);
    ElMessage.error("加载视频列表失败");
  } finally {
    loading.value = false;
  }
};

/**
 * 加载更多视频
 */
const loadMoreVideos = async () => {
  if (!hasMore.value || loading.value) return;

  currentPage.value++;
  await loadVideos(true);
};

/**
 * 搜索
 */
const handleSearch = () => {
  if (!searchKeyword.value.trim()) {
    ElMessage.warning("请输入搜索关键词");
    return;
  }

  // 保存搜索历史
  const history = JSON.parse(localStorage.getItem("searchHistory") || "[]");
  if (!history.includes(searchKeyword.value)) {
    history.unshift(searchKeyword.value);
    if (history.length > 10) {
      history.pop();
    }
    localStorage.setItem("searchHistory", JSON.stringify(history));
  }

  // 更新URL
  router.push({
    path: "/search",
    query: {
      keyword: searchKeyword.value,
      ...(currentCategory.value && { category_id: currentCategory.value }),
    },
  });
};

/**
 * 选择分类
 */
const selectCategory = (categoryId) => {
  currentCategory.value = categoryId;
  currentPage.value = 1;

  // 更新URL
  const query = {};
  if (currentKeyword.value) {
    query.keyword = currentKeyword.value;
  }
  if (categoryId) {
    query.category_id = categoryId;
  }

  router.push({
    path: "/search",
    query,
  });
};

/**
 * 点击视频
 */
const handleVideoClick = (video) => {
  router.push(`/videos/${video.id}`);
};

/**
 * 稍后再看
 */
const handleWatchLater = (video) => {
  ElMessage.success(`已添加到稍后再看：${video.title}`);
};

// 格式化视频时长（秒 -> MM:SS 或 HH:MM:SS）
const formatDuration = (seconds) => {
  if (!seconds) return "00:00";

  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;

  if (hours > 0) {
    return `${hours.toString().padStart(2, "0")}:${minutes
      .toString()
      .padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  }
  return `${minutes.toString().padStart(2, "0")}:${secs
    .toString()
    .padStart(2, "0")}`;
};

/**
 * 认证相关
 */
const showAuthDialog = (mode) => {
  authMode.value = mode;
  authDialogVisible.value = true;
};

const handleAuthSuccess = () => {
  console.log("登录注册成功");
};

const handleCommand = async (command) => {
  if (command === "profile") {
    router.push("/profile");
  } else if (command === "logout") {
    try {
      await ElMessageBox.confirm("确定要退出登录吗？", "提示", {
        confirmButtonText: "确定",
        cancelButtonText: "取消",
        type: "warning",
      });
      await userStore.logout();
      ElMessage.success("退出登录成功");
      location.reload();
    } catch (error) {
      if (error !== "cancel") {
        console.error("退出登录失败:", error);
      }
    }
  }
};
</script>

<style scoped>
.search-page {
  min-height: 100vh;
  background: var(--bg-light);
}

/* ==================== 顶部导航栏 ==================== */
.app-header {
  background: var(--bg-white);
  box-shadow: var(--shadow-sm);
  position: sticky;
  top: 0;
  z-index: var(--z-index-sticky);
}

.header-wrapper {
  max-width: var(--container-max-width);
  margin: 0 auto;
  padding: 0 var(--spacing-lg);
  height: var(--header-height);
  display: flex;
  align-items: center;
  gap: var(--spacing-lg);
}

/* Logo */
.logo {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  cursor: pointer;
  flex-shrink: 0;
  transition: transform var(--transition-fast);
}

.logo:hover {
  transform: scale(1.05);
}

.logo-icon {
  width: 32px;
  height: 32px;
  color: var(--primary-color);
}

.logo-text {
  font-size: var(--font-size-xl);
  font-weight: bold;
  background: linear-gradient(
    135deg,
    var(--primary-color),
    var(--secondary-color)
  );
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

/* 搜索框 */
.search-box {
  position: relative;
  flex: 1;
  max-width: 500px;
  display: flex;
  background: var(--bg-light);
  border-radius: var(--radius-lg);
  overflow: hidden;
  transition: all var(--transition-base);
}

.search-box:focus-within {
  background: var(--bg-white);
  box-shadow: 0 0 0 2px var(--primary-light);
}

.search-input {
  flex: 1;
  padding: var(--spacing-sm) var(--spacing-md);
  font-size: var(--font-size-base);
  color: var(--text-primary);
  border: none;
  outline: none;
  background: transparent;
}

.search-input::placeholder {
  color: var(--text-placeholder);
}

.search-btn {
  padding: var(--spacing-sm) var(--spacing-md);
  color: var(--text-secondary);
  cursor: pointer;
  transition: color var(--transition-fast);
  border: none;
  background: transparent;
}

.search-btn:hover {
  color: var(--primary-color);
}

/* 用户操作区 */
.user-actions {
  display: flex;
  align-items: center;
  gap: var(--spacing-base);
  flex-shrink: 0;
}

.user-info {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-xs) var(--spacing-base);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: background var(--transition-fast);
}

.user-info:hover {
  background: var(--bg-light);
}

.user-name {
  font-size: var(--font-size-base);
  max-width: 80px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.upload-btn {
  background: var(--primary-color);
  border-color: var(--primary-color);
  color: var(--text-white);
  font-weight: 500;
}

.upload-btn:hover {
  background: var(--primary-hover);
  border-color: var(--primary-hover);
}

/* ==================== 主内容区 ==================== */
.main-content {
  padding: var(--spacing-lg) 0;
}

.content-container {
  max-width: var(--container-max-width);
  margin: 0 auto;
  padding: 0 var(--spacing-lg);
}

/* 搜索信息栏 */
.search-info {
  margin-bottom: var(--spacing-lg);
}

.search-title {
  font-size: var(--font-size-2xl);
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 var(--spacing-sm) 0;
}

.keyword {
  color: var(--primary-color);
}

.search-meta {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}

/* 分类筛选栏 */
.filter-bar {
  background: var(--bg-white);
  border-radius: var(--radius-md);
  padding: var(--spacing-md);
  margin-bottom: var(--spacing-lg);
}

.filter-section {
  display: flex;
  align-items: flex-start;
  gap: var(--spacing-md);
}

.filter-label {
  font-size: var(--font-size-base);
  font-weight: 500;
  color: var(--text-regular);
  white-space: nowrap;
  padding-top: var(--spacing-xs);
}

.filter-options {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-sm);
  flex: 1;
}

.filter-option {
  padding: var(--spacing-xs) var(--spacing-md);
  background: var(--bg-light);
  border-radius: var(--radius-base);
  font-size: var(--font-size-sm);
  color: var(--text-regular);
  cursor: pointer;
  transition: all var(--transition-fast);
  user-select: none;
}

.filter-option:hover {
  background: var(--primary-light);
  color: var(--primary-color);
}

.filter-option.is-active {
  background: var(--primary-color);
  color: var(--text-white);
}

/* ==================== 响应式设计 ==================== */
@media (max-width: 768px) {
  .header-wrapper {
    padding: 0 var(--spacing-md);
    gap: var(--spacing-md);
  }

  .search-box {
    max-width: none;
  }

  .user-name {
    display: none;
  }

  .content-container {
    padding: 0 var(--spacing-md);
  }

  .filter-section {
    flex-direction: column;
    gap: var(--spacing-sm);
  }
}
</style>
