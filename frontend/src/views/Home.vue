<template>
  <div class="home-page">
    <AppHeader
      @login="
        authMode = 'login';
        authVisible = true;
      "
      @register="
        authMode = 'register';
        authVisible = true;
      "
    />

    <main class="main-content">
      <div class="channel-layout">
        <div
          v-for="cat in categories"
          :key="cat.id"
          class="channel-link"
          :class="{ active: currentCategory === cat.id }"
          @click="selectCategory(cat.id)"
        >
          {{ cat.name }}
        </div>
      </div>

      <div class="video-grid-wrapper">
        <VideoGrid
          :videos="videos"
          :loading="loading"
          :has-more="hasMore"
          @load-more="loadMoreVideos"
          @video-click="router.push(`/videos/${$event.id}`)"
        />
      </div>
    </main>

    <AuthDialog v-model="authVisible" :mode="authMode" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import AppHeader from "@/components/layout/AppHeader.vue";
import VideoGrid from "@/components/video/VideoGrid.vue";
import AuthDialog from "@/components/AuthDialog.vue";
import { getVideoList } from "@/api/video";
import { getCategories } from "@/api/category";
import type { Video, Category } from "@/types/entity";

const router = useRouter();
const categories = ref<Category[]>([]);
const videos = ref<Video[]>([]);
const currentCategory = ref<number | null>(null);
const loading = ref(false);
const hasMore = ref(true);
const page = ref(1);

const authVisible = ref(false);
const authMode = ref("login");

const loadData = async (reset = false) => {
  if (loading.value) return;
  loading.value = true;

  if (reset) {
    page.value = 1;
    videos.value = [];
  }

  try {
    const res = await getVideoList({
      page: page.value,
      page_size: 20,
      category_id: currentCategory.value,
    });

    // 因为用了 TS，这里有自动补全
    if (res.success && res.data.items) {
      videos.value.push(...res.data.items);
      hasMore.value = videos.value.length < res.data.total;
      page.value++;
    }
  } finally {
    loading.value = false;
  }
};

const selectCategory = (id: number) => {
  currentCategory.value = id;
  loadData(true);
};

onMounted(() => {
  getCategories().then((res) => {
    if (res.success) categories.value = res.data;
  });
  loadData(true);
});

const loadMoreVideos = () => loadData();
</script>

<style lang="scss" scoped>
.home-page {
  min-height: 100vh;
  background-color: var(--bg-light);
}

.main-content {
  max-width: 1400px; // B站常见宽屏宽度
  margin: 0 auto;
  padding: 20px;

  // 响应式布局优化
  @media (max-width: 1400px) {
    padding: 10px;
  }
}

.channel-layout {
  display: flex;
  gap: 24px;
  padding: 10px 0 20px;
  margin-bottom: 10px;
  overflow-x: auto;

  .channel-link {
    font-size: 16px;
    color: var(--text-regular);
    cursor: pointer;
    white-space: nowrap;
    padding: 6px 12px;
    border-radius: 6px;
    transition: all 0.2s;

    &:hover {
      color: var(--primary-color);
      background-color: var(--bg-white);
    }

    &.active {
      color: var(--primary-color);
      background-color: rgba(251, 114, 153, 0.1); // B站粉淡色背景
      font-weight: 600;
    }
  }
}
</style>
