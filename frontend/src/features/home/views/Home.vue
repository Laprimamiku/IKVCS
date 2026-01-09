<template>
  <div class="home-page">
    <AppHeader @login="handleLogin" @register="handleRegister" />

    <main class="main-content">
      <!-- Category Navigation -->
      <div class="category-section">
        <CategoryNav
          :categories="categories"
          :active="currentCategory"
          @select="handleCategorySelect"
        />
      </div>

      <!-- Main Feed Area -->
      <div class="feed-container">
        <!-- Banner + Video Grid -->
        <div class="bili-grid">
          <!-- Featured Banner (spans 2 columns, 2 rows) -->
          <div class="grid-banner">
            <HomeBanner :banners="banners" @click="handleBannerClick" />
          </div>

          <!-- Video Cards -->
          <template v-if="videos.length > 0">
            <VideoCard
              v-for="(video, index) in videos"
              :key="video.id"
              :video="video"
              class="grid-video-item"
              :class="{ 'animate-in': true }"
              :style="{ animationDelay: `${index * 0.03}s` }"
              @click="handleVideoClick"
            />
          </template>

          <!-- Loading Skeletons -->
          <template v-else-if="loading">
            <div v-for="i in 12" :key="i" class="skeleton-card">
              <div class="skeleton-cover"></div>
              <div class="skeleton-info">
                <div class="skeleton-title"></div>
                <div class="skeleton-meta"></div>
              </div>
            </div>
          </template>

          <!-- Empty State -->
          <EmptyState
            v-else-if="!loading && videos.length === 0"
            title="暂无视频内容"
            description="快去上传第一个视频吧~"
            :icon="VideoCamera"
            :icon-size="48"
            size="medium"
          />
        </div>

        <!-- Load More Section -->
        <div class="feed-bottom">
          <template v-if="loading && videos.length > 0">
            <div class="loading-more">
              <div class="loading-spinner"></div>
              <span>加载中...</span>
            </div>
          </template>
          <template v-else-if="hasMore">
            <el-button class="load-more-btn" @click="loadMoreVideos">
              <span>加载更多</span>
              <el-icon class="arrow-icon"><ArrowDown /></el-icon>
            </el-button>
          </template>
          <template v-else-if="videos.length > 0">
            <div class="no-more">
              <span class="divider-line"></span>
              <span class="no-more-text">没有更多了，去投个稿吧~</span>
              <span class="divider-line"></span>
            </div>
          </template>
        </div>
      </div>
    </main>

    <!-- Auth Dialog -->
    <AuthDialog v-model="authVisible" :mode="authMode" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from "vue";
import { useRouter } from "vue-router";
import { ArrowDown, VideoCamera } from "@element-plus/icons-vue";
import AppHeader from "@/shared/components/layout/AppHeader.vue";
import EmptyState from "@/shared/components/atoms/EmptyState.vue";
import CategoryNav from "@/features/home/components/CategoryNav.vue";
import HomeBanner from "@/features/home/components/HomeBanner.vue";
import VideoCard from "@/features/video/shared/components/VideoCard.vue";
import AuthDialog from "@/features/auth/components/AuthDialog.vue";
import { getVideoList } from "@/features/video/shared/api/video.api";
import { getPublicCategories } from "@/features/video/shared/api/category.api";
import { getRecommendations } from "@/features/recommendation/api/recommendation.api";
import type { Video, Category, PageResult } from "@/shared/types/entity";

const router = useRouter();

// State
const allVideos = ref<Video[]>([]); // 存储所有视频
const bannerVideos = ref<Video[]>([]); // 轮播图视频
const loading = ref(false);
const hasMore = ref(true);
const currentPage = ref(1);
const pageSize = ref(20);
const categories = ref<Category[]>([]);
const currentCategory = ref<number | null>(null);
const authVisible = ref(false);
const authMode = ref<"login" | "register">("login");

// 推荐算法已实现：
// 1. 热门推荐（播放量、点赞数、收藏数加权）
// 2. 同类推荐（同分类/同作者）
// 3. 个性化推荐（基于用户观看/点赞/收藏行为）
// 4. 去重与冷启动（新用户显示热门+最新）

// 计算属性：过滤掉轮播图中的视频，避免重复显示
const videos = computed(() => {
  const bannerVideoIds = new Set(bannerVideos.value.map(v => v.id));
  return allVideos.value.filter(v => !bannerVideoIds.has(v.id));
});

// 轮播图数据转换
const banners = computed(() => {
  return bannerVideos.value.map(video => ({
    id: video.id,
    title: video.title,
    description: video.description || `UP主: ${video.uploader?.nickname || '未知'}`,
    image: video.cover_url || '/default-cover.jpg',
    link: `/videos/${video.id}`,
    video: video // 保存完整视频信息，用于点击跳转
  }));
});

// 获取轮播图视频（最新上传的3个视频）
const loadBannerVideos = async () => {
  try {
    // 推荐页（currentCategory 为 null）显示所有分类的最新视频
    // 其他分类页只显示该分类下的最新视频
    const res = await getVideoList({
      page: 1,
      page_size: 3, // 获取最新的3个视频作为轮播图
      category_id: currentCategory.value, // 如果是推荐页则为 null，其他分类页则为对应的 category_id
    });
    
    if (res.success) {
      const data = res.data as PageResult<Video>;
      bannerVideos.value = (data.items || []).slice(0, 3); // 确保最多3个视频
    }
  } catch (e) {
    console.error("Failed to load banner videos:", e);
  }
};

// Load categories
const loadCategories = async () => {
  try {
    const res = await getPublicCategories();
    categories.value = Array.isArray(res) ? res : res.data || [];
  } catch (e) {
    console.error("Failed to load categories:", e);
  }
};

// Load videos
const loadVideos = async (append = false) => {
  if (loading.value) return;
  loading.value = true;
  
  try {
    if (!append) {
      currentPage.value = 1;
      allVideos.value = [];
    }
    
    // 计算需要跳过的视频数量（轮播图视频数量）
    const skipCount = bannerVideos.value.length;
    const actualPage = append ? currentPage.value : 1;
    
    let res;
    // 如果是推荐页（currentCategory 为 null），使用推荐 API
    if (currentCategory.value === null && actualPage === 1) {
      res = await getRecommendations({
        scene: "home",
        limit: pageSize.value + skipCount,
      });
    } else {
      // 其他情况使用普通列表 API
      res = await getVideoList({
        page: actualPage,
        page_size: pageSize.value + (actualPage === 1 ? skipCount : 0), // 第一页多获取几个，用于过滤轮播图视频
        category_id: currentCategory.value,
      });
    }
    
    if (res.success) {
      const data = res.data as PageResult<Video>;
      let newVideos = data.items || [];
      
      // 如果是第一页，需要过滤掉轮播图中的视频
      if (actualPage === 1) {
        const bannerVideoIds = new Set(bannerVideos.value.map(v => v.id));
        newVideos = newVideos.filter(v => !bannerVideoIds.has(v.id));
        // 确保获得足够的视频数量
        newVideos = newVideos.slice(0, pageSize.value);
      }
      
      allVideos.value = append ? [...allVideos.value, ...newVideos] : newVideos;
      hasMore.value = allVideos.value.length < (data.total || 0) - skipCount;
      currentPage.value++;
    }
  } catch (e) {
    console.error("Failed to load videos:", e);
  } finally {
    loading.value = false;
  }
};

// Event handlers
const loadMoreVideos = () => loadVideos(true);

const handleCategorySelect = async (id: number | null) => {
  currentCategory.value = id;
  // 先加载轮播图，再加载视频列表
  await loadBannerVideos();
  await loadVideos();
};

const handleVideoClick = (v: Video) => {
  router.push(`/videos/${v.id}`);
};

// 处理轮播图点击事件
const handleBannerClick = (item: { id: number; title: string }) => {
  if (item.video) {
    router.push(`/videos/${item.video.id}`);
  }
};

const handleLogin = () => {
  authMode.value = "login";
  authVisible.value = true;
};

const handleRegister = () => {
  authMode.value = "register";
  authVisible.value = true;
};

// Lifecycle
onMounted(async () => {
  await loadCategories();
  await loadBannerVideos(); // 先加载轮播图视频
  await loadVideos(); // 再加载其他视频
});
</script>

<style lang="scss" scoped>
.home-page {
  min-height: 100vh;
  background-color: var(--bg-global);
}

.main-content {
  max-width: var(--container-max-width);
  margin: 0 auto;
  padding: 0 var(--content-padding) var(--space-10);
}

/* Category Section */
.category-section {
  padding: var(--space-4) 0;
  margin-bottom: var(--space-2);
}

/* Feed Container */
.feed-container {
  width: 100%;
}

/* Bilibili-style Grid Layout */
.bili-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: var(--space-5);
  grid-auto-rows: min-content;
}

/* Banner spans 2 columns x 2 rows */
.grid-banner {
  grid-column: span 2;
  grid-row: span 2;
  border-radius: var(--radius-lg);
  overflow: hidden;
  min-height: 380px;
  background: var(--bg-gray-1);

  :deep(.home-banner),
  :deep(.el-carousel),
  :deep(.el-carousel__container) {
    height: 100% !important;
    margin-bottom: 0;
  }
}

/* Video Card Animation */
.grid-video-item {
  width: 100%;
  opacity: 0;
  
  &.animate-in {
    animation: fadeInUp 0.4s ease-out forwards;
  }
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Skeleton Loading */
.skeleton-card {
  width: 100%;
  
  .skeleton-cover {
    width: 100%;
    padding-top: 56.25%;
    border-radius: var(--radius-md);
    background: linear-gradient(
      90deg,
      var(--bg-gray-1) 25%,
      var(--bg-gray-2) 50%,
      var(--bg-gray-1) 75%
    );
    background-size: 200% 100%;
    animation: skeleton-loading 1.5s infinite;
  }
  
  .skeleton-info {
    padding: var(--space-3) 0;
  }
  
  .skeleton-title {
    height: var(--font-size-lg);
    width: 90%;
    background: linear-gradient(
      90deg,
      var(--bg-gray-1) 25%,
      var(--bg-gray-2) 50%,
      var(--bg-gray-1) 75%
    );
    background-size: 200% 100%;
    animation: skeleton-loading 1.5s infinite;
    border-radius: var(--radius-sm);
    margin-bottom: var(--space-2);
  }
  
  .skeleton-meta {
    height: var(--font-size-sm);
    width: 60%;
    background: linear-gradient(
      90deg,
      var(--bg-gray-1) 25%,
      var(--bg-gray-2) 50%,
      var(--bg-gray-1) 75%
    );
    background-size: 200% 100%;
    animation: skeleton-loading 1.5s infinite;
    border-radius: var(--radius-sm);
  }
}

@keyframes skeleton-loading {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* Empty State */
.empty-state {
  grid-column: 1 / -1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-16) var(--space-6);
  color: var(--text-tertiary);
  
  .empty-icon {
    font-size: var(--font-size-5xl);
    margin-bottom: var(--space-4);
  }
  
  .empty-text {
    font-size: var(--font-size-lg);
    margin-bottom: var(--space-2);
  }
  
  .empty-hint {
    font-size: var(--font-size-sm);
  }
}

/* Feed Bottom */
.feed-bottom {
  margin-top: var(--space-10);
  display: flex;
  justify-content: center;
}

.loading-more {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  color: var(--text-tertiary);
  font-size: var(--font-size-sm);
  
  .loading-spinner {
    width: var(--space-5);
    height: var(--space-5);
    border: 2px solid var(--border-color);
    border-top-color: var(--bili-pink);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.load-more-btn {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-8);
  height: var(--btn-height-xl);
  background: var(--bg-white);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-round);
  color: var(--text-secondary);
  font-size: var(--font-size-base);
  cursor: pointer;
  transition: var(--transition-base);
  
  .arrow-icon {
    transition: transform var(--transition-base);
  }
  
  &:hover {
    border-color: var(--bili-pink);
    color: var(--bili-pink);
    
    .arrow-icon {
      transform: translateY(2px);
    }
  }
}

.no-more {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  color: var(--text-tertiary);
  font-size: var(--font-size-sm);
  
  .divider-line {
    width: 60px;
    height: 1px; /* 保持 1px 细线 */
    background: var(--border-color);
  }
  
  .no-more-text {
    white-space: nowrap;
  }
}

/* Responsive Design */
@media (max-width: 1400px) {
  .bili-grid {
    grid-template-columns: repeat(4, 1fr);
  }
}

@media (max-width: 1100px) {
  .bili-grid {
    grid-template-columns: repeat(3, 1fr);
    gap: var(--space-4);
  }
  
  .grid-banner {
    grid-column: span 3;
    grid-row: span 1;
    min-height: 280px;
  }
}

@media (max-width: 768px) {
  .main-content {
    padding: 0 var(--content-padding-mobile) var(--space-8);
  }
  
  .bili-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: var(--space-3);
  }
  
  .grid-banner {
    grid-column: span 2;
    min-height: 200px;
  }
}

@media (max-width: 480px) {
  .bili-grid {
    grid-template-columns: 1fr;
    gap: var(--space-4);
  }
  
  .grid-banner {
    grid-column: span 1;
    min-height: 180px;
  }
}
</style>
