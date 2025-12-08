<template>
  <div class="home-page">
    <!-- 顶部导航栏 -->
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
            @focus="showSearchPanel = true"
            @blur="handleSearchBlur"
          />
          <button class="search-btn" @click="handleSearch">
            <el-icon><Search /></el-icon>
          </button>

          <!-- 搜索下拉面板 -->
          <div v-show="showSearchPanel" class="search-dropdown">
            <!-- 搜索历史 -->
            <div v-if="searchHistory.length" class="search-section">
              <div class="section-header">
                <span>搜索历史</span>
                <el-button text size="small" @click="clearHistory">
                  清空
                </el-button>
              </div>
              <div class="history-list">
                <span
                  v-for="(item, index) in searchHistory"
                  :key="index"
                  class="history-item"
                  @click="selectHistory(item)"
                >
                  {{ item }}
                </span>
              </div>
            </div>

            <!-- 热搜榜 -->
            <div class="search-section">
              <div class="section-header">
                <span>热搜榜</span>
              </div>
              <div class="trending-list">
                <div
                  v-for="(item, index) in trendingSearches"
                  :key="index"
                  class="trending-item"
                  @click="selectTrending(item)"
                >
                  <span class="rank" :class="{ 'rank-top': index < 3 }">
                    {{ index + 1 }}
                  </span>
                  <span class="keyword">{{ item }}</span>
                </div>
              </div>
            </div>
          </div>
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
              class="auth-button login-btn"
              @click="showAuthDialog('login')"
            >
              登录
            </el-button>
            <el-button
              type="primary"
              plain
              size="small"
              class="auth-button register-btn"
              @click="showAuthDialog('register')"
            >
              注册
            </el-button>
          </template>
        </div>
      </div>
    </header>

    <!-- 分类导航 -->
    <nav class="category-nav">
      <div class="nav-wrapper">
        <div
          v-for="cat in categories"
          :key="cat.id"
          class="nav-item"
          :class="{ 'is-active': currentCategory === cat.id }"
          @click="selectCategory(cat.id)"
        >
          <el-icon><component :is="cat.icon" /></el-icon>
          <span>{{ cat.name }}</span>
        </div>
      </div>
    </nav>

    <!-- 主内容区 -->
    <main class="main-content">
      <div class="content-container">
        <!-- 轮播图 -->
        <HomeBanner :banners="banners" @click="handleBannerClick" />

        <!-- 视频区域 -->
        <div class="video-section">
          <h2 class="section-title">
            <template v-if="currentCategory">
              {{
                categories.find((c) => c.id === currentCategory)?.name ||
                "推荐"
              }}视频
            </template>
            <template v-else> 推荐视频 </template>
          </h2>
          <VideoGrid
            :videos="videos"
            :loading="loading"
            :has-more="hasMore"
            @load-more="loadMoreVideos"
            @video-click="handleVideoClick"
            @watch-later="handleWatchLater"
          />
        </div>
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
import { ref, reactive, onMounted } from "vue";
import { useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  Search,
  User,
  ArrowDown,
  SwitchButton,
  Upload,
  Star,
  Film,
  Reading,
  Monitor,
  Headset,
  TrophyBase,
} from "@element-plus/icons-vue";
import { useUserStore } from "@/stores/user";
import AuthDialog from "@/components/AuthDialog.vue";
import HomeBanner from "@/components/home/HomeBanner.vue";
import VideoGrid from "@/components/video/VideoGrid.vue";
import { getVideoList } from "@/api/video";
import { getCategories } from "@/api/category";

const router = useRouter();
const userStore = useUserStore();

// 搜索相关
const searchKeyword = ref("");
const showSearchPanel = ref(false);
const searchHistory = ref(["Vue 3 教程", "Element Plus", "前端开发"]);
const trendingSearches = ref([
  "AI 技术解析",
  "Vue 3 新特性",
  "前端性能优化",
  "TypeScript 入门",
  "React vs Vue",
  "Web3.0 趋势",
  "微前端架构",
  "Vite 构建工具",
  "CSS 动画技巧",
  "JavaScript 设计模式",
]);

// 分类相关
const currentCategory = ref(null);
const categories = ref([]);

// 加载分类列表
const loadCategories = async () => {
  try {
    const response = await getCategories();
    if (response.success) {
      // 添加"推荐"选项
      categories.value = [
        { id: null, name: "推荐", icon: Star },
        ...(response.data || []).map((cat) => ({
          ...cat,
          icon: Film, // 可以根据分类类型设置不同图标
        })),
      ];
    }
  } catch (error) {
    console.error("加载分类失败:", error);
    // 使用默认分类
    categories.value = [
      { id: null, name: "推荐", icon: Star },
      { id: 1, name: "科技", icon: Monitor },
      { id: 2, name: "教育", icon: Reading },
      { id: 3, name: "娱乐", icon: Film },
    ];
  }
};

// 轮播图数据
const banners = ref([
  {
    id: 1,
    title: "精彩视频推荐",
    description: "发现更多优质内容",
    image: "https://picsum.photos/1400/400?random=1",
    link: "/video/1",
  },
  {
    id: 2,
    title: "热门番剧",
    description: "追番必看",
    image: "https://picsum.photos/1400/400?random=2",
    link: "/bangumi/1",
  },
  {
    id: 3,
    title: "音乐专区",
    description: "聆听美妙旋律",
    image: "https://picsum.photos/1400/400?random=3",
    link: "/music/1",
  },
]);

// 视频数据
const loading = ref(false);
const hasMore = ref(true);
const currentPage = ref(1);
const pageSize = ref(20);
const videos = ref([]);

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

// 加载视频列表
const loadVideos = async (append = false) => {
  if (loading.value) return;

  loading.value = true;

  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value,
    };

    // 添加分类筛选
    if (currentCategory.value) {
      params.category_id = currentCategory.value;
    }

    const response = await getVideoList(params);

    if (response.success) {
      const newVideos = (response.data.items || []).map((video) => ({
        id: video.id,
        title: video.title,
        cover: video.cover_url,
        duration: formatDuration(video.duration),
        views: video.view_count,
        likes: video.like_count || 0,
        danmaku: video.danmaku_count || 0, // 从后端获取弹幕数
        author: {
          name:
            video.uploader?.nickname || video.uploader?.username || "未知用户",
          avatar: video.uploader?.avatar || "",
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

      hasMore.value = videos.value.length < (response.data.total || 0);
    }
  } catch (error) {
    console.error("加载视频列表失败:", error);
    ElMessage.error("加载视频列表失败");
  } finally {
    loading.value = false;
  }
};

// 加载更多视频
const loadMoreVideos = async () => {
  if (!hasMore.value || loading.value) return;

  currentPage.value++;
  await loadVideos(true);
};

// 选择分类
const selectCategory = (categoryId) => {
  currentCategory.value = categoryId;
  currentPage.value = 1;
  loadVideos();
};

// 认证弹窗
const authDialogVisible = ref(false);
const authMode = ref("login");

onMounted(async () => {
  if (userStore.token && !userStore.userInfo) {
    try {
      await userStore.initUserInfo();
    } catch (error) {
      console.error("初始化用户信息失败:", error);
    }
  }
  // 加载分类列表
  await loadCategories();

  // 加载视频列表
  await loadVideos();

  // 加载搜索历史
  const savedHistory = localStorage.getItem("searchHistory");
  if (savedHistory) {
    try {
      searchHistory.value = JSON.parse(savedHistory);
    } catch (error) {
      console.error("加载搜索历史失败:", error);
    }
  }
});

// 搜索相关方法
const handleSearch = () => {
  if (!searchKeyword.value.trim()) {
    ElMessage.warning("请输入搜索关键词");
    return;
  }

  // 添加到搜索历史
  if (!searchHistory.value.includes(searchKeyword.value)) {
    searchHistory.value.unshift(searchKeyword.value);
    if (searchHistory.value.length > 10) {
      searchHistory.value.pop();
    }
    // 保存到localStorage
    localStorage.setItem("searchHistory", JSON.stringify(searchHistory.value));
  }

  // 跳转到搜索页面
  router.push({
    path: "/search",
    query: {
      keyword: searchKeyword.value,
    },
  });

  showSearchPanel.value = false;
};

const handleSearchBlur = () => {
  // 延迟关闭，以便点击事件能够触发
  setTimeout(() => {
    showSearchPanel.value = false;
  }, 200);
};

const selectHistory = (keyword) => {
  searchKeyword.value = keyword;
  handleSearch();
};

const selectTrending = (keyword) => {
  searchKeyword.value = keyword;
  handleSearch();
};

const clearHistory = () => {
  searchHistory.value = [];
  localStorage.removeItem("searchHistory");
};

// 轮播图相关方法
const handleBannerClick = (banner) => {
  console.log("点击轮播图:", banner);
  if (banner.link) {
    router.push(banner.link);
  }
};

// 视频相关方法
const handleVideoClick = (video) => {
  router.push(`/videos/${video.id}`);
};

const handleWatchLater = (video) => {
  console.log("稍后再看:", video);
  ElMessage.success(`已添加到稍后再看：${video.title}`);
};

// 认证相关方法
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
.home-page {
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
}

.search-box input,
.search-box button {
  border: none;
  outline: none;
  background: transparent;
}

.search-box {
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
}

.search-input::placeholder {
  color: var(--text-placeholder);
}

.search-btn {
  padding: var(--spacing-sm) var(--spacing-md);
  color: var(--text-secondary);
  cursor: pointer;
  transition: color var(--transition-fast);
}

.search-btn:hover {
  color: var(--primary-color);
}

/* 搜索下拉面板 */
.search-dropdown {
  position: absolute;
  top: calc(100% + var(--spacing-sm));
  left: 0;
  right: 0;
  background: var(--bg-white);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  padding: var(--spacing-md);
  z-index: var(--z-index-dropdown);
  animation: fadeInUp 0.3s ease;
}

.search-section {
  margin-bottom: var(--spacing-md);
}

.search-section:last-child {
  margin-bottom: 0;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--spacing-sm);
  font-size: var(--font-size-sm);
  font-weight: 500;
  color: var(--text-regular);
}

.history-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-sm);
}

.history-item {
  padding: var(--spacing-xs) var(--spacing-base);
  background: var(--bg-light);
  border-radius: var(--radius-base);
  font-size: var(--font-size-sm);
  color: var(--text-regular);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.history-item:hover {
  background: var(--primary-light);
  color: var(--primary-color);
}

.trending-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.trending-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-xs) var(--spacing-sm);
  border-radius: var(--radius-base);
  cursor: pointer;
  transition: background var(--transition-fast);
}

.trending-item:hover {
  background: var(--bg-light);
}

.rank {
  width: 20px;
  text-align: center;
  font-size: var(--font-size-sm);
  font-weight: 500;
  color: var(--text-secondary);
}

.rank-top {
  color: var(--primary-color);
  font-weight: bold;
}

.keyword {
  flex: 1;
  font-size: var(--font-size-sm);
  color: var(--text-regular);
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

/* 登录注册按钮样式 */
.auth-button {
  font-weight: 500;
  border-radius: var(--radius-base);
  transition: all var(--transition-fast);
}

.login-btn {
  background: var(--primary-color);
  border-color: var(--primary-color);
  color: var(--text-white);
}

.login-btn:hover {
  background: var(--primary-hover);
  border-color: var(--primary-hover);
}

.register-btn {
  background: transparent;
  border-color: var(--primary-color);
  color: var(--primary-color);
}

.register-btn:hover {
  background: var(--primary-light);
  border-color: var(--primary-hover);
  color: var(--primary-hover);
}

/* 上传按钮样式 */
.upload-btn {
  background: var(--primary-color);
  border-color: var(--primary-color);
  color: var(--text-white);
  font-weight: 500;
  margin-right: var(--spacing-base);
}

.upload-btn:hover {
  background: var(--primary-hover);
  border-color: var(--primary-hover);
}

/* ==================== 分类导航 ==================== */
.category-nav {
  background: var(--bg-white);
  border-bottom: 1px solid var(--border-light);
  position: sticky;
  top: var(--header-height);
  z-index: calc(var(--z-index-sticky) - 1);
}

.nav-wrapper {
  max-width: var(--container-max-width);
  margin: 0 auto;
  padding: 0 var(--spacing-lg);
  display: flex;
  gap: var(--spacing-2xl);
  overflow-x: auto;
  scrollbar-width: none;
}

.nav-wrapper::-webkit-scrollbar {
  display: none;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  padding: var(--spacing-md) 0;
  font-size: var(--font-size-base);
  color: var(--text-regular);
  cursor: pointer;
  position: relative;
  white-space: nowrap;
  transition: color var(--transition-fast);
}

.nav-item:hover {
  color: var(--primary-color);
}

.nav-item.is-active {
  color: var(--primary-color);
  font-weight: 500;
}

.nav-item.is-active::after {
  content: "";
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: var(--primary-color);
  border-radius: var(--radius-sm) var(--radius-sm) 0 0;
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

/* 视频区域 */
.video-section {
  margin-top: var(--spacing-xl);
}

.section-title {
  font-size: var(--font-size-xl);
  font-weight: 600;
  margin-bottom: var(--spacing-md);
  color: var(--text-primary);
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

  .nav-wrapper {
    padding: 0 var(--spacing-md);
    gap: var(--spacing-lg);
  }

  .content-container {
    padding: 0 var(--spacing-md);
  }
}
</style>
