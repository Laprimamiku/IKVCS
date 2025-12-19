<template>
  <div class="home-page">
    <AppHeader
      @login="handleLogin"
      @register="handleRegister"
    />

    <main class="main-content">
      <!-- 分类导航 -->
      <CategoryNav
        :categories="categories"
        :active="currentCategory"
        @select="handleCategorySelect"
      />

      <!-- 轮播图 -->
      <HomeBanner
        v-if="banners.length > 0"
        :banners="banners"
        class="banner-section"
      />

      <!-- 视频列表 -->
      <div class="video-grid-wrapper">
        <VideoGrid
          :videos="videos"
          :loading="loading"
          @video-click="handleVideoClick"
        />
        
        <!-- 加载更多 -->
        <div v-if="hasMore && !loading" class="load-more-wrapper">
          <el-button
            type="primary"
            :loading="loading"
            @click="loadMoreVideos"
          >
            加载更多
          </el-button>
        </div>
        
        <!-- 加载中 -->
        <div v-if="loading" class="loading-wrapper">
          <el-icon class="is-loading"><Loading /></el-icon>
          <span>加载中...</span>
        </div>
        
        <!-- 无更多数据 -->
        <div v-if="!hasMore && videos.length > 0" class="no-more">
          没有更多视频了
        </div>
      </div>
    </main>

    <AuthDialog v-model="authVisible" :mode="authMode" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import { Loading } from "@element-plus/icons-vue";
import AppHeader from "@/shared/components/layout/AppHeader.vue";
import CategoryNav from "@/features/home/components/CategoryNav.vue";
import HomeBanner from "@/features/home/components/HomeBanner.vue";
import VideoGrid from "@/features/video/shared/components/VideoGrid.vue";
import AuthDialog from "@/features/auth/components/AuthDialog.vue";
import { getVideoList } from "@/features/video/shared/api/video.api";
import { getCategories } from "@/features/video/shared/api/category.api";
import type { Video, Category, PageResult } from "@/shared/types/entity";
import { cache } from "@/shared/utils/cache";

const router = useRouter();

// 视频列表相关状态
const videos = ref<Video[]>([]);
const loading = ref(false);
const hasMore = ref(true);
const currentPage = ref(1);
const pageSize = ref(12); // 优化：减少初始加载数量，提升首屏速度

// 分类相关状态
const categories = ref<Category[]>([]);
const currentCategory = ref<number | null>(null);

// 认证对话框
const authVisible = ref(false);
const authMode = ref<"login" | "register">("login");

// 轮播图数据（可以从 API 获取，这里使用示例数据）
const banners = ref([
  {
    id: 1,
    title: "欢迎来到 IKVCS",
    description: "一个现代化的视频分享平台",
    image: "https://via.placeholder.com/1920x600",
    link: "/",
  },
]);

// 加载分类列表（带缓存）
const loadCategories = async () => {
  const cacheKey = 'categories';
  
  // 先检查缓存
  const cached = cache.get<Category[]>(cacheKey);
  if (cached) {
    categories.value = cached;
    return;
  }
  
  try {
    const response = await getCategories();
    let categoryData: Category[] = [];
    
    if (response && response.data && Array.isArray(response.data)) {
      categoryData = response.data as Category[];
    } else if (Array.isArray(response)) {
      categoryData = response as Category[];
    }
    
    categories.value = categoryData;
    
    // 缓存分类数据（10分钟，因为分类变化不频繁）
    if (categoryData.length > 0) {
      cache.set(cacheKey, categoryData, 10 * 60 * 1000);
    }
  } catch (error) {
    console.error("加载分类失败:", error);
  }
};

// 加载视频列表
const loadVideos = async (append = false) => {
  if (loading.value) return;
  loading.value = true;

  try {
    if (!append) {
      currentPage.value = 1;
      videos.value = [];
    }

    const response = await getVideoList({
      page: currentPage.value,
      page_size: pageSize.value,
      category_id: currentCategory.value,
    });

    if (response.success) {
      const data = response.data as PageResult<Video>;
      if (append) {
        videos.value.push(...(data.items || []));
      } else {
        videos.value = data.items || [];
      }
      hasMore.value = videos.value.length < (data.total || 0);
      currentPage.value++;
    }
  } catch (error) {
    console.error("加载视频列表失败:", error);
  } finally {
    loading.value = false;
  }
};

// 加载更多视频
const loadMoreVideos = () => {
  loadVideos(true);
};

// 处理分类选择
const handleCategorySelect = (categoryId: number | null) => {
  currentCategory.value = categoryId;
  loadVideos();
};

// 处理视频点击
const handleVideoClick = (video: Video) => {
  router.push(`/videos/${video.id}`);
};

// 处理登录
const handleLogin = () => {
  authMode.value = "login";
  authVisible.value = true;
};

// 处理注册
const handleRegister = () => {
  authMode.value = "register";
  authVisible.value = true;
};

// 初始化 - 并行加载分类和视频，提升加载速度
onMounted(async () => {
  // 并行加载分类和视频，而不是串行等待
  await Promise.all([
    loadCategories(),
    loadVideos()
  ]);
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
  padding: 20px 24px 40px;

  @media (max-width: 1400px) {
    padding: 16px 20px 32px;
  }
}

.banner-section {
  margin-bottom: 24px;
}

.video-grid-wrapper {
  margin-top: 20px;
}

.load-more-wrapper {
  display: flex;
  justify-content: center;
  margin-top: 32px;
  padding: 24px 0;

  :deep(.el-button) {
    background: var(--primary-color);
    border-color: var(--primary-color);
    color: #fff;
    padding: 10px 32px;
    border-radius: var(--radius-md);
    font-weight: 500;
    transition: all 0.2s;

    &:hover {
      background: var(--primary-hover);
      border-color: var(--primary-hover);
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(250, 114, 152, 0.3);
    }
  }
}

.loading-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 48px 0;
  color: var(--text-tertiary);
  font-size: var(--font-size-sm);

  .el-icon {
    font-size: 24px;
    color: var(--primary-color);
    animation: rotate 1s linear infinite;
  }
}

@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.no-more {
  text-align: center;
  padding: 32px 0;
  color: var(--text-tertiary);
  font-size: var(--font-size-sm);
}
</style>



