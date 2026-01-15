<template>
  <div class="bili-search-page">
    <!-- 顶部导航栏 -->
    <AppHeader />

    <!-- 主内容区 -->
    <main class="main-content">
      <div class="content-container">
        <!-- 搜索结果头部 -->
        <div class="search-header">
          <div class="search-info">
            <h1 class="search-title">
              <template v-if="currentKeyword">
                搜索：<span class="keyword">{{ currentKeyword }}</span>
              </template>
              <template v-else>全部视频</template>
            </h1>
            <div class="search-meta">
              <span class="result-count">共 {{ formatNumber(total) }} 个结果</span>
              <span class="search-time">{{ searchTime }}</span>
            </div>
          </div>
          
          <!-- 排序选项 -->
          <div class="sort-options">
            <div class="sort-label">排序：</div>
            <div class="sort-tabs">
              <div 
                class="sort-tab" 
                :class="{ active: sortType === 'default' }"
                @click="handleSortChange('default')"
              >
                综合排序
              </div>
              <div 
                class="sort-tab" 
                :class="{ active: sortType === 'newest' }"
                @click="handleSortChange('newest')"
              >
                最新发布
              </div>
              <div 
                class="sort-tab" 
                :class="{ active: sortType === 'popular' }"
                @click="handleSortChange('popular')"
              >
                最多播放
              </div>
            </div>
          </div>
        </div>

        <!-- 筛选栏 -->
        <div class="filter-section">
          <div class="filter-group">
            <span class="filter-label">分区：</span>
            <div class="filter-options">
              <div 
                class="filter-option" 
                :class="{ active: currentCategory === null }"
                @click="handleCategoryChange(null)"
              >
                全部
              </div>
              <div 
                v-for="category in categories" 
                :key="category.id"
                class="filter-option" 
                :class="{ active: currentCategory === category.id }"
                @click="handleCategoryChange(category.id)"
              >
                {{ category.name }}
              </div>
            </div>
          </div>
        </div>

        <!-- 视频列表 -->
        <div class="video-section">
          <!-- 加载状态 -->
          <div v-if="loading && videos.length === 0" class="loading-grid">
            <div v-for="i in 12" :key="i" class="video-skeleton">
              <div class="skeleton-cover"></div>
              <div class="skeleton-info">
                <div class="skeleton-title"></div>
                <div class="skeleton-meta"></div>
              </div>
            </div>
          </div>

          <!-- 视频网格 -->
          <div v-else-if="videos.length > 0" class="video-grid">
            <div 
              v-for="video in videos" 
              :key="video.id"
              class="video-card"
              @click="handleVideoClick(video)"
            >
              <div class="video-cover">
                <img :src="video.cover_url || '/placeholder-video.jpg'" :alt="video.title" />
                <div class="video-duration">{{ formatDuration(video.duration) }}</div>
                <div class="video-play-count">
                  <el-icon><VideoPlay /></el-icon>
                  {{ formatNumber(video.view_count || 0) }}
                </div>
              </div>
              <div class="video-info">
                <h3 class="video-title">{{ video.title }}</h3>
                <div class="video-meta">
                  <div class="uploader">
                    <el-icon><User /></el-icon>
                    {{ video.uploader?.nickname || video.uploader?.username || '未知用户' }}
                  </div>
                  <div class="upload-time">{{ formatTime(video.created_at) }}</div>
                </div>
                <div class="video-stats">
                  <span class="stat-item">
                    <el-icon><VideoPlay /></el-icon>
                    {{ formatNumber(video.view_count || 0) }}
                  </span>
                  <span class="stat-item">
                    <el-icon><ChatDotRound /></el-icon>
                    {{ formatNumber(video.danmaku_count || 0) }}
                  </span>
                </div>
              </div>
            </div>
          </div>

          <!-- 空状态 -->
          <div v-else class="empty-state">
            <el-icon class="empty-icon" :size="48"><Search /></el-icon>
            <div class="empty-title">没有找到相关视频</div>
            <div class="empty-desc">
              <template v-if="currentKeyword">
                试试其他关键词，或者
                <span class="link" @click="clearSearch">浏览全部视频</span>
              </template>
              <template v-else>
                暂时没有视频内容
              </template>
            </div>
          </div>
        </div>

        <!-- 加载更多 -->
        <div v-if="hasMore && videos.length > 0" class="load-more-section">
          <el-button 
            class="load-more-btn"
            :loading="loading"
            @click="loadMoreVideos"
          >
            {{ loading ? '加载中...' : '点击加载更多' }}
          </el-button>
        </div>

        <!-- 到底了 -->
        <div v-if="!hasMore && videos.length > 0" class="no-more-section">
          <div class="no-more-line"></div>
          <span class="no-more-text">没有更多了</span>
          <div class="no-more-line"></div>
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

<script setup lang="ts">
import { ref, onMounted, watch, computed } from "vue";
import { useRouter, useRoute } from "vue-router";
import { ElMessage } from "element-plus";
import { VideoPlay, ChatDotRound, User, Search } from "@element-plus/icons-vue";
import AppHeader from "@/shared/components/layout/AppHeader.vue";
import AuthDialog from "@/features/auth/components/AuthDialog.vue";
import { getPublicCategories } from "@/features/video/shared/api/category.api";
import { searchVideos, getSearchSuggestions } from "../api/search.api";
import type { Video, Category } from "@/shared/types/entity";

const router = useRouter();
const route = useRoute();

// 搜索相关
const currentKeyword = ref<string>("");
const sortType = ref<string>("default");

// 分类相关
const currentCategory = ref<number | null>(null);
const categories = ref<Category[]>([]);

const { handleError, handleApiError } = useErrorHandler({
  messagePrefix: '搜索'
});

// 视频数据
const videos = ref<Video[]>([]);
const loading = ref<boolean>(false);
const total = ref<number>(0);
const currentPage = ref<number>(1);
const pageSize = ref<number>(20);
const hasMore = ref<boolean>(true);

// 认证弹窗
const authDialogVisible = ref<boolean>(false);
const authMode = ref<"login" | "register">("login");

// 搜索时间
const searchTime = computed(() => {
  const now = new Date();
  return `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;
});

/**
 * 格式化数字
 */
const formatNumber = (num: number): string => {
  if (!num) return "0";
  if (num >= 100000000) return (num / 100000000).toFixed(1) + "亿";
  if (num >= 10000) return (num / 10000).toFixed(1) + "万";
  return num.toString();
};

/**
 * 格式化时长
 */
const formatDuration = (seconds: number): string => {
  if (!seconds) return "00:00";
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
};

/**
 * 格式化时间
 */
const formatTime = (dateStr: string): string => {
  if (!dateStr) return "";
  const date = new Date(dateStr);
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const days = Math.floor(diff / (1000 * 60 * 60 * 24));
  
  if (days === 0) return "今天";
  if (days === 1) return "昨天";
  if (days < 7) return `${days}天前`;
  if (days < 30) return `${Math.floor(days / 7)}周前`;
  if (days < 365) return `${Math.floor(days / 30)}个月前`;
  return `${Math.floor(days / 365)}年前`;
};

/**
 * 初始化
 */
onMounted(async () => {
  // 从URL获取搜索关键词
  if (route.query.keyword) {
    currentKeyword.value = route.query.keyword as string;
  }

  // 从URL获取分类
  if (route.query.category_id) {
    currentCategory.value = parseInt(route.query.category_id as string);
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
      currentKeyword.value = (newQuery.keyword as string) || "";
      currentCategory.value = newQuery.category_id
        ? parseInt(newQuery.category_id as string)
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
    const response = await getPublicCategories();

    if (response && response.data && Array.isArray(response.data)) {
      categories.value = response.data as Category[];
    } else if (Array.isArray(response)) {
      categories.value = response as Category[];
    } else {
      categories.value = [];
    }
  } catch (error) {
    console.error("加载分类失败:", error);
    categories.value = [];
  }
};

/**
 * 加载视频列表（使用新的搜索 API）
 */
const loadVideos = async (append = false) => {
  if (loading.value) return;

  loading.value = true;

  try {
    // 构建搜索参数
    const params = {
      q: currentKeyword.value || undefined,
      category_id: currentCategory.value || undefined,
      page: currentPage.value,
      page_size: pageSize.value,
      sort_by: getSortField(sortType.value),
      order: "desc",
    };

    const response = await searchVideos(params as any);

    if (response.success && response.data) {
      const newVideos = response.data.items || [];

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
 * 获取排序字段
 */
const getSortField = (sortType: string): "created" | "view" | "like" => {
  const map: Record<string, "created" | "view" | "like"> = {
    "default": "created",
    "newest": "created",
    "popular": "view",
  };
  return map[sortType] || "created";
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
 * 点击视频
 */
const handleVideoClick = (video: Video) => {
  router.push(`/videos/${video.id}`);
};

/**
 * 排序变化
 */
const handleSortChange = (type: string) => {
  sortType.value = type;
  currentPage.value = 1;
  loadVideos();
};

/**
 * 分类变化
 */
const handleCategoryChange = (categoryId: number | null) => {
  currentCategory.value = categoryId;
  currentPage.value = 1;

  // 更新URL
  const query: Record<string, string | number> = {};
  if (currentKeyword.value) {
    query.keyword = currentKeyword.value;
  }
  if (categoryId !== null) {
    query.category_id = categoryId;
  }

  router.push({
    path: "/search",
    query,
  });
};

/**
 * 清除搜索
 */
const clearSearch = () => {
  router.push("/search");
};

/**
 * 认证相关
 */
const handleAuthSuccess = () => {
  console.log("登录注册成功");
};
</script>

<style lang="scss" scoped>
.bili-search-page {
  min-height: 100vh;
  background: #f4f5f7;
}

.main-content {
  padding: 20px 0;
}

.content-container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 20px;
}

/* 搜索头部 */
.search-header {
  background: #fff;
  border-radius: 8px;
  padding: 24px;
  margin-bottom: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.search-info {
  margin-bottom: 20px;
}

.search-title {
  font-size: 24px;
  font-weight: 600;
  color: #18191c;
  margin: 0 0 8px;
  
  .keyword {
    color: #00aeec;
  }
}

.search-meta {
  display: flex;
  align-items: center;
  gap: 16px;
  font-size: 14px;
  color: #61666d;
  
  .result-count {
    font-weight: 500;
  }
  
  .search-time {
    &::before {
      content: '•';
      margin-right: 8px;
    }
  }
}

/* 排序选项 */
.sort-options {
  display: flex;
  align-items: center;
  gap: 12px;
}

.sort-label {
  font-size: 14px;
  color: #61666d;
  font-weight: 500;
}

.sort-tabs {
  display: flex;
  gap: 4px;
}

.sort-tab {
  padding: 6px 16px;
  border-radius: 20px;
  font-size: 14px;
  color: #61666d;
  cursor: pointer;
  transition: all 0.2s;
  
  &:hover {
    background: #f1f2f3;
    color: #18191c;
  }
  
  &.active {
    background: #00aeec;
    color: #fff;
  }
}

/* 筛选栏 */
.filter-section {
  background: #fff;
  border-radius: 8px;
  padding: 16px 24px;
  margin-bottom: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 12px;
}

.filter-label {
  font-size: 14px;
  color: #61666d;
  font-weight: 500;
  flex-shrink: 0;
}

.filter-options {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.filter-option {
  padding: 4px 12px;
  border-radius: 16px;
  font-size: 13px;
  color: #61666d;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid #e3e5e7;
  
  &:hover {
    border-color: #00aeec;
    color: #00aeec;
  }
  
  &.active {
    background: #00aeec;
    border-color: #00aeec;
    color: #fff;
  }
}

/* 视频区域 */
.video-section {
  background: #fff;
  border-radius: 8px;
  padding: 24px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  margin-bottom: 20px;
}

/* 加载骨架屏 */
.loading-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
}

.video-skeleton {
  .skeleton-cover {
    width: 100%;
    aspect-ratio: 16/9;
    background: linear-gradient(90deg, #f1f2f3 25%, #e3e5e7 50%, #f1f2f3 75%);
    background-size: 200% 100%;
    animation: skeleton-loading 1.5s infinite;
    border-radius: 6px;
    margin-bottom: 12px;
  }
  
  .skeleton-info {
    .skeleton-title {
      height: 16px;
      background: linear-gradient(90deg, #f1f2f3 25%, #e3e5e7 50%, #f1f2f3 75%);
      background-size: 200% 100%;
      animation: skeleton-loading 1.5s infinite;
      border-radius: 4px;
      margin-bottom: 8px;
    }
    
    .skeleton-meta {
      height: 12px;
      width: 60%;
      background: linear-gradient(90deg, #f1f2f3 25%, #e3e5e7 50%, #f1f2f3 75%);
      background-size: 200% 100%;
      animation: skeleton-loading 1.5s infinite;
      border-radius: 4px;
    }
  }
}

@keyframes skeleton-loading {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* 视频网格 */
.video-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
}

.video-card {
  cursor: pointer;
  transition: transform 0.2s;
  
  &:hover {
    transform: translateY(-2px);
    
    .video-cover img {
      transform: scale(1.05);
    }
  }
}

.video-cover {
  position: relative;
  width: 100%;
  aspect-ratio: 16/9;
  border-radius: 6px;
  overflow: hidden;
  margin-bottom: 12px;
  
  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    transition: transform 0.3s;
  }
  
  .video-duration {
    position: absolute;
    bottom: 6px;
    right: 6px;
    background: rgba(0, 0, 0, 0.8);
    color: #fff;
    padding: 2px 6px;
    border-radius: 3px;
    font-size: 12px;
    font-weight: 500;
  }
  
  .video-play-count {
    position: absolute;
    bottom: 6px;
    left: 6px;
    background: rgba(0, 0, 0, 0.8);
    color: #fff;
    padding: 2px 6px;
    border-radius: 3px;
    font-size: 12px;
    display: flex;
    align-items: center;
    gap: 2px;
    
    .el-icon {
      font-size: 12px;
    }
  }
}

.video-info {
  .video-title {
    font-size: 14px;
    font-weight: 500;
    color: #18191c;
    line-height: 1.4;
    margin: 0 0 8px;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
  
  .video-meta {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 8px;
    font-size: 12px;
    color: #61666d;
    
    .uploader {
      display: flex;
      align-items: center;
      gap: 4px;
      
      .el-icon {
        font-size: 12px;
      }
    }
  }
  
  .video-stats {
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 12px;
    color: #61666d;
    
    .stat-item {
      display: flex;
      align-items: center;
      gap: 2px;
      
      .el-icon {
        font-size: 12px;
      }
    }
  }
}

/* 空状态 */
.empty-state {
  text-align: center;
  padding: 60px 20px;
  
  .empty-icon {
    font-size: 64px;
    margin-bottom: 16px;
  }
  
  .empty-title {
    font-size: 18px;
    font-weight: 500;
    color: #18191c;
    margin-bottom: 8px;
  }
  
  .empty-desc {
    font-size: 14px;
    color: #61666d;
    
    .link {
      color: #00aeec;
      cursor: pointer;
      
      &:hover {
        text-decoration: underline;
      }
    }
  }
}

/* 加载更多 */
.load-more-section {
  text-align: center;
  padding: 24px;
}

.load-more-btn {
  min-width: 200px;
  height: 40px;
  border-radius: 20px;
  background: #f1f2f3;
  border: none;
  color: #61666d;
  font-size: 14px;
  
  &:hover {
    background: #e3e5e7;
    color: #18191c;
  }
}

/* 到底了 */
.no-more-section {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  gap: 16px;
}

.no-more-line {
  flex: 1;
  height: 1px;
  background: #e3e5e7;
  max-width: 100px;
}

.no-more-text {
  font-size: 14px;
  color: #9499a0;
}

/* 响应式 */
@media (max-width: 1200px) {
  .content-container {
    padding: 0 16px;
  }
  
  .video-grid {
    grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
    gap: 16px;
  }
}

@media (max-width: 768px) {
  .content-container {
    padding: 0 12px;
  }
  
  .search-header,
  .filter-section,
  .video-section {
    padding: 16px;
    margin-bottom: 12px;
  }
  
  .search-title {
    font-size: 20px;
  }
  
  .sort-options {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
  
  .filter-group {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
  
  .video-grid {
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 12px;
  }
  
  .loading-grid {
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 12px;
  }
}
</style>
