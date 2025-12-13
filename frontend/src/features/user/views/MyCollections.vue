<template>
  <div class="my-collections">
    <div class="page-header">
      <h2>我的收藏</h2>
    </div>

    <div v-loading="loading" class="collection-list">
      <div v-if="!loading && videos.length === 0" class="empty-state">
        <el-empty description="还没有收藏视频哦" />
      </div>

      <div v-else class="video-grid">
        <VideoCard
          v-for="video in videos"
          :key="video.id"
          :video="video"
          class="collection-item"
        />
      </div>

      <div class="pagination-container" v-if="total > pageSize">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="total"
          layout="prev, pager, next"
          @current-change="handlePageChange"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { getMyCollections } from "@/features/video/shared/api/video.api";
import VideoCard from "@/features/video/shared/components/VideoCard.vue";
import type { Video } from "@/shared/types/entity";

const loading = ref(false);
const videos = ref<Video[]>([]);
const currentPage = ref(1);
const pageSize = ref(20);
const total = ref(0);

const fetchCollections = async () => {
  loading.value = true;
  try {
    const res = await getMyCollections({
      page: currentPage.value,
      page_size: pageSize.value,
    });
    if (res.success && res.data) {
      videos.value = res.data.items;
      total.value = res.data.total;
    }
  } finally {
    loading.value = false;
  }
};

const handlePageChange = (page: number) => {
  currentPage.value = page;
  fetchCollections();
};

onMounted(() => {
  fetchCollections();
});
</script>

<style lang="scss" scoped>
.my-collections {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;

  .page-header {
    margin-bottom: 24px;
    h2 {
      font-size: 20px;
      color: #18191c;
      font-weight: 500;
    }
  }

  .video-grid {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 20px;

    @media (max-width: 1400px) {
      grid-template-columns: repeat(4, 1fr);
    }
    @media (max-width: 1100px) {
      grid-template-columns: repeat(3, 1fr);
    }
    @media (max-width: 768px) {
      grid-template-columns: repeat(2, 1fr);
    }
  }

  .pagination-container {
    display: flex;
    justify-content: center;
    margin-top: 40px;
  }
}
</style>
