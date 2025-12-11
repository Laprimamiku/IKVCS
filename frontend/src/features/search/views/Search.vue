<template>
  <div class="search-page">
    <!-- 顶部导航栏 -->
    <AppHeader />

    <!-- 主内容区 -->
    <main class="main-content">
      <div class="content-container">
        <!-- 搜索信息栏 -->
        <SearchInfo :keyword="currentKeyword" :total="total" />

        <!-- 分类筛选 -->
        <SearchFilterBar v-model="currentCategory" :categories="categories" />

        <!-- 视频列表 -->
        <VideoGrid
          :videos="videos"
          :loading="loading"
          @video-click="handleVideoClick"
        />

        <!-- 加载更多按钮 -->
        <div v-if="hasMore && !loading" class="load-more-section">
          <el-button @click="loadMoreVideos" :loading="loading">
            加载更多
          </el-button>
        </div>

        <!-- 加载中 -->
        <div v-if="loading" class="loading-section">
          <el-icon class="is-loading"><Loading /></el-icon>
          <span>加载中...</span>
        </div>

        <!-- 无更多数据 -->
        <div v-if="!hasMore && videos.length > 0" class="no-more-section">
          没有更多了
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
import { ref, onMounted, watch } from "vue";
import { useRouter, useRoute } from "vue-router";
import { ElMessage } from "element-plus";
import { Loading } from "@element-plus/icons-vue";
import AppHeader from "@/shared/components/layout/AppHeader.vue";
import SearchInfo from "@/features/search/components/SearchInfo.vue";
import SearchFilterBar from "@/features/search/components/SearchFilterBar.vue";
import VideoGrid from "@/features/video/shared/components/VideoGrid.vue";
import AuthDialog from "@/features/auth/components/AuthDialog.vue";
import { getVideoList } from "@/features/video/shared/api/video.api";
import { getCategories } from "@/features/video/shared/api/category.api";
import type {
  Video,
  Category,
  PageResult,
  VideoQueryParams,
} from "@/shared/types/entity";

const router = useRouter();
const route = useRoute();

// 搜索相关
const currentKeyword = ref<string>("");

// 分类相关
const currentCategory = ref<number | null>(null);
const categories = ref<Category[]>([]);

// 视频数据 - 使用 Video[] 类型
const videos = ref<Video[]>([]);
const loading = ref<boolean>(false);
const total = ref<number>(0);
const currentPage = ref<number>(1);
const pageSize = ref<number>(20);
const hasMore = ref<boolean>(true);

// 认证弹窗
const authDialogVisible = ref<boolean>(false);
const authMode = ref<"login" | "register">("login");

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
 * 监听分类变化
 */
watch(currentCategory, (newCategory) => {
  currentPage.value = 1;

  // 更新URL
  const query: Record<string, string | number> = {};
  if (currentKeyword.value) {
    query.keyword = currentKeyword.value;
  }
  if (newCategory !== null) {
    query.category_id = newCategory;
  }

  router.push({
    path: "/search",
    query,
  });
});

/**
 * 加载分类列表
 */
const loadCategories = async () => {
  try {
    const response = await getCategories();

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
 * 加载视频列表
 */
const loadVideos = async (append = false) => {
  if (loading.value) return;

  loading.value = true;

  try {
    const params: VideoQueryParams = {
      page: currentPage.value,
      page_size: pageSize.value,
      keyword: currentKeyword.value || undefined,
      category_id: currentCategory.value || null,
    };

    const response = await getVideoList(params);

    if (response.success) {
      const data = response.data as PageResult<Video>;
      const newVideos = data.items || [];

      if (append) {
        videos.value.push(...newVideos);
      } else {
        videos.value = newVideos;
      }

      total.value = data.total || 0;
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
 * 点击视频
 */
const handleVideoClick = (video: Video) => {
  router.push(`/videos/${video.id}`);
};

/**
 * 认证相关
 */
const handleAuthSuccess = () => {
  console.log("登录注册成功");
};
</script>

<style lang="scss" scoped>
.search-page {
  min-height: 100vh;
  background: var(--bg-light);
}

.main-content {
  padding: var(--spacing-lg) 0;
}

.content-container {
  max-width: var(--container-max-width);
  margin: 0 auto;
  padding: 0 var(--spacing-lg);
}

.load-more-section,
.loading-section,
.no-more-section {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: var(--spacing-xl) 0;
  color: var(--text-secondary);
  font-size: var(--font-size-sm);
}

.loading-section {
  gap: var(--spacing-sm);
}

@media (max-width: 768px) {
  .content-container {
    padding: 0 var(--spacing-md);
  }
}
</style>
