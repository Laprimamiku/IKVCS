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
        <SearchFilterBar v-model="currentCategory" :categories="categories" @update:model-value="handleCategoryChange" />

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

<script setup lang="ts">
import { ref, onMounted, watch } from "vue";
import { useRouter, useRoute } from "vue-router";
import { ElMessage } from "element-plus";
import AppHeader from "@/components/layout/AppHeader.vue";
import SearchInfo from "@/components/search/SearchInfo.vue";
import SearchFilterBar from "@/components/search/SearchFilterBar.vue";
import VideoGrid from "@/components/video/VideoGrid.vue";
import AuthDialog from "@/components/AuthDialog.vue";
import { getVideoList } from "@/api/video";
import { getCategories } from "@/api/category";
import { formatDuration } from "@/utils/formatters";
import type { Video, Category, PageResult, VideoQueryParams } from "@/types/entity";

const router = useRouter();
const route = useRoute();

// 搜索相关
const currentKeyword = ref<string>("");

// 分类相关
const currentCategory = ref<number | null>(null);
const categories = ref<Category[]>([]);

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
      const newVideos = (data.items || []).map((video) => ({
        id: video.id,
        title: video.title,
        cover: video.cover_url,
        duration: formatDuration(video.duration),
        views: video.view_count,
        likes: video.like_count || 0,
        danmaku: video.danmaku_count || 0,
        author: {
          name:
            video.uploader?.nickname || video.uploader?.username || "未知用户",
          avatar: video.uploader?.avatar || "",
          verified: false,
          verifiedType: "personal" as const,
        },
        tags: [] as string[],
        publishTime: video.created_at,
      }));

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
 * 选择分类
 */
const handleCategoryChange = (categoryId: number | null) => {
  currentCategory.value = categoryId;
  currentPage.value = 1;

  // 更新URL
  const query: Record<string, string | number> = {};
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
const handleVideoClick = (video: { id: number }) => {
  router.push(`/videos/${video.id}`);
};

/**
 * 稍后再看
 */
const handleWatchLater = (video: { title: string }) => {
  ElMessage.success(`已添加到稍后再看：${video.title}`);
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

@media (max-width: 768px) {
  .content-container {
    padding: 0 var(--spacing-md);
  }
}
</style>
