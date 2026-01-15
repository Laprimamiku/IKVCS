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
                搜索{{ searchType === 'uploader' ? 'UP主' : '视频' }}：
                <span class="keyword">{{ currentKeyword }}</span>
              </template>
              <template v-else>
                {{ searchType === 'uploader' ? 'UP主搜索' : '全部视频' }}
              </template>
            </h1>
            <div class="search-meta">
              <span class="result-count">
                共 {{ formatNumber(total) }} 个{{ searchType === 'uploader' ? 'UP主' : '视频' }}
              </span>
              <span class="search-time">{{ searchTime }}</span>
            </div>
          </div>

          <div class="search-controls">
            <div class="type-tabs">
              <div
                class="type-tab"
                :class="{ active: searchType === 'video' }"
                @click="handleTypeChange('video')"
              >
                视频
              </div>
              <div
                class="type-tab"
                :class="{ active: searchType === 'uploader' }"
                @click="handleTypeChange('uploader')"
              >
                UP主
              </div>
            </div>

            <!-- 排序选项 -->
            <div class="sort-options" v-if="searchType === 'video'">
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
        </div>

        <!-- 视频列表 -->
        <div class="video-section" v-if="searchType === 'video'">
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

        <!-- UP主列表 -->
        <div class="user-section" v-else>
          <div v-if="loading && users.length === 0" class="user-skeleton-list">
            <div v-for="i in 6" :key="i" class="user-skeleton">
              <div class="skeleton-avatar"></div>
              <div class="skeleton-info">
                <div class="skeleton-title"></div>
                <div class="skeleton-meta"></div>
              </div>
            </div>
          </div>

          <div v-else-if="users.length > 0" class="user-list">
            <div
              v-for="user in users"
              :key="user.id"
              class="user-card"
              @click="handleUserClick(user)"
            >
              <el-avatar :size="48" :src="user.avatar">
                {{ (user.nickname || user.username).charAt(0).toUpperCase() }}
              </el-avatar>
              <div class="user-info">
                <div class="user-name">{{ user.nickname || user.username }}</div>
                <div class="user-meta">@{{ user.username }}</div>
              </div>
              <div class="user-action">进入主页</div>
            </div>
          </div>

          <div v-else class="empty-state">
            <el-icon class="empty-icon" :size="48"><Search /></el-icon>
            <div class="empty-title">
              {{ currentKeyword ? '没有找到该UP主' : '请输入UP主名称进行搜索' }}
            </div>
            <div class="empty-desc">
              <template v-if="currentKeyword">
                请确认名称完整匹配，或切换到
                <span class="link" @click="handleTypeChange('video')">视频搜索</span>
              </template>
              <template v-else>
                支持用户名或昵称的精确查询
              </template>
            </div>
          </div>
        </div>

        <!-- 加载更多 -->
        <div v-if="hasMore && (videos.length > 0 || users.length > 0)" class="load-more-section">
          <el-button 
            class="load-more-btn"
            :loading="loading"
            @click="loadMoreResults"
          >
            {{ loading ? '加载中...' : '点击加载更多' }}
          </el-button>
        </div>

        <!-- 到底了 -->
        <div v-if="!hasMore && (videos.length > 0 || users.length > 0)" class="no-more-section">
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
import { searchVideos, searchUsers } from "../api/search.api";
import type { Video, UserBrief } from "@/shared/types/entity";

const router = useRouter();
const route = useRoute();

// 搜索相关
const currentKeyword = ref<string>("");
const searchType = ref<"video" | "uploader">("video");
const sortType = ref<string>("default");

// 视频/用户数据
const videos = ref<Video[]>([]);
const users = ref<UserBrief[]>([]);
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

const normalizeSearchType = (value: unknown): "video" | "uploader" => {
  const raw = Array.isArray(value) ? value[0] : value;
  return raw === "uploader" ? "uploader" : "video";
};

const buildQuery = () => {
  const query: Record<string, string | number> = {};
  if (searchType.value === "uploader") {
    query.type = "uploader";
  }
  if (currentKeyword.value) {
    query.keyword = currentKeyword.value;
  }
  return query;
};

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
  searchType.value = normalizeSearchType(route.query.type);

  // 从URL获取搜索关键词
  if (route.query.keyword) {
    currentKeyword.value = route.query.keyword as string;
  }

  // 加载搜索结果
  await loadResults();
});

/**
 * 监听路由变化
 */
watch(
  () => route.query,
  (newQuery) => {
    const nextType = normalizeSearchType(newQuery.type);
    const nextKeyword = (newQuery.keyword as string) || "";

    if (
      nextType !== searchType.value ||
      nextKeyword !== currentKeyword.value
    ) {
      searchType.value = nextType;
      currentKeyword.value = nextKeyword;
      currentPage.value = 1;
      loadResults();
    }
  }
);

/**
 * 加载搜索结果
 */
const loadResults = async (append = false) => {
  if (searchType.value === "video") {
    if (!append) {
      users.value = [];
    }
    await loadVideos(append);
    return;
  }

  if (!append) {
    videos.value = [];
  }
  await loadUsers(append);
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
 * 加载UP主列表（精确匹配）
 */
const loadUsers = async (append = false) => {
  if (loading.value) return;

  if (!currentKeyword.value.trim()) {
    users.value = [];
    total.value = 0;
    hasMore.value = false;
    return;
  }

  loading.value = true;

  try {
    const params = {
      q: currentKeyword.value.trim(),
      page: currentPage.value,
      page_size: pageSize.value,
    };

    const response = await searchUsers(params);

    if (response.success && response.data) {
      const newUsers = response.data.items || [];

      if (append) {
        users.value.push(...newUsers);
      } else {
        users.value = newUsers;
      }

      total.value = response.data.total || 0;
      hasMore.value = users.value.length < total.value;
    }
  } catch (error) {
    console.error("加载UP主列表失败:", error);
    ElMessage.error("加载UP主列表失败");
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
 * 加载更多结果
 */
const loadMoreResults = async () => {
  if (!hasMore.value || loading.value) return;

  currentPage.value++;
  await loadResults(true);
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
  loadResults();
};

/**
 * 搜索类型切换
 */
const handleTypeChange = (type: "video" | "uploader") => {
  if (searchType.value === type) return;
  searchType.value = type;
  currentPage.value = 1;
  router.push({ path: "/search", query: buildQuery() });
  loadResults();
};

/**
 * 点击UP主
 */
const handleUserClick = (user: UserBrief) => {
  router.push(`/users/${user.id}`);
};

/**
 * 清除搜索
 */
const clearSearch = () => {
  const query: Record<string, string> = {};
  if (searchType.value === "uploader") {
    query.type = "uploader";
  }
  router.push({ path: "/search", query });
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

.search-controls {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.type-tabs {
  display: flex;
  gap: 4px;
  padding: 4px;
  border-radius: 999px;
  background: #f1f2f3;
}

.type-tab {
  padding: 6px 16px;
  border-radius: 999px;
  font-size: 14px;
  color: #61666d;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: #e3e5e7;
    color: #18191c;
  }

  &.active {
    background: #00aeec;
    color: #fff;
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

/* 视频区域 */
.video-section {
  background: #fff;
  border-radius: 8px;
  padding: 24px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  margin-bottom: 20px;
}

.user-section {
  background: #fff;
  border-radius: 8px;
  padding: 24px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  margin-bottom: 20px;
}

.user-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.user-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 16px;
  border: 1px solid #e3e5e7;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    border-color: #00aeec;
    box-shadow: 0 2px 6px rgba(0, 174, 236, 0.12);
  }
}

.user-info {
  flex: 1;
  min-width: 0;

  .user-name {
    font-size: 15px;
    font-weight: 600;
    color: #18191c;
    margin-bottom: 4px;
  }

  .user-meta {
    font-size: 12px;
    color: #61666d;
  }
}

.user-action {
  font-size: 12px;
  color: #00aeec;
  font-weight: 500;
}

.user-skeleton-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.user-skeleton {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 16px;
  border: 1px solid #e3e5e7;
  border-radius: 8px;

  .skeleton-avatar {
    width: 48px;
    height: 48px;
    border-radius: 50%;
    background: linear-gradient(90deg, #f1f2f3 25%, #e3e5e7 50%, #f1f2f3 75%);
    background-size: 200% 100%;
    animation: skeleton-loading 1.5s infinite;
  }

  .skeleton-info {
    flex: 1;
  }

  .skeleton-title {
    height: 16px;
    width: 160px;
    margin-bottom: 8px;
    background: linear-gradient(90deg, #f1f2f3 25%, #e3e5e7 50%, #f1f2f3 75%);
    background-size: 200% 100%;
    animation: skeleton-loading 1.5s infinite;
    border-radius: 4px;
  }

  .skeleton-meta {
    height: 12px;
    width: 120px;
    background: linear-gradient(90deg, #f1f2f3 25%, #e3e5e7 50%, #f1f2f3 75%);
    background-size: 200% 100%;
    animation: skeleton-loading 1.5s infinite;
    border-radius: 4px;
  }
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
  .video-section,
  .user-section {
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

  .search-controls {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }

  .type-tabs {
    width: 100%;
  }
  
  .video-grid {
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 12px;
  }
  
  .loading-grid {
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 12px;
  }

  .user-card {
    align-items: flex-start;
  }

  .user-action {
    display: none;
  }
}
</style>
