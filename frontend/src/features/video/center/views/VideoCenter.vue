<template>
  <div class="video-center-page">
    <!-- 顶部操作栏 -->
    <VideoCenterHeader @upload="handleUpload" />

    <!-- 状态筛选 -->
    <VideoStatusFilter
      v-model="statusFilter"
      @update:model-value="handleStatusChange"
    />

    <!-- 视频列表 -->
    <div class="video-list">
      <el-empty
        v-if="!loading && videos.length === 0"
        description="暂无视频，快去上传吧~"
      />
      <div v-else class="video-grid">
        <VideoCenterItem
          v-for="video in videos"
          :key="video.id"
          :video="video"
          @view="handleView"
          @edit="handleEdit"
          @delete="handleDelete"
        />
      </div>
    </div>

    <!-- 分页 -->
    <el-pagination
      v-if="total > 0"
      v-model:current-page="currentPage"
      :page-size="pageSize"
      :total="total"
      layout="total, prev, pager, next"
      @current-change="loadVideos"
      class="pagination"
    />

    <!-- 编辑对话框 -->
    <VideoEditDialog
      v-model="editDialogVisible"
      :video="editingVideo"
      :categories="categories"
      @save="handleSaveEdit"
      @cancel="editDialogVisible = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from "vue";
import { useRouter } from "vue-router";
import VideoCenterHeader from "@/features/video/center/components/VideoCenterHeader.vue";
import VideoStatusFilter from "@/features/video/center/components/VideoStatusFilter.vue";
import VideoCenterItem from "@/features/video/center/components/VideoCenterItem.vue";
import VideoEditDialog from "@/features/video/center/components/VideoEditDialog.vue";
import { useVideoManagement } from "@/features/video/center/composables/useVideoManagement";
import type { Video } from "@/shared/types/entity";

const router = useRouter();

// 使用视频管理 Composable
const {
  videos,
  loading,
  currentPage,
  pageSize,
  total,
  statusFilter,
  categories,
  loadVideos,
  loadCategories,
  handleStatusChange,
  viewVideo,
  deleteVideoItem,
  updateVideoInfo,
} = useVideoManagement();

const editDialogVisible = ref(false);
const editingVideo = ref<Video | null>(null);

// 操作处理
const handleUpload = () => {
  router.push("/upload");
};

const handleView = (videoId: number) => {
  viewVideo(videoId);
};

const handleEdit = (video: Video) => {
  editingVideo.value = video;
  editDialogVisible.value = true;
};

const handleDelete = async (video: Video) => {
  await deleteVideoItem(video);
};

// 保存编辑
const handleSaveEdit = async (data: {
  id: number;
  title: string;
  description: string;
  category_id: number | null;
  cover_file: File | null;
  subtitle_file: File | null;
}) => {
  const success = await updateVideoInfo(data.id, {
    title: data.title,
    description: data.description,
    category_id: data.category_id || undefined,
    cover_file: data.cover_file,
    subtitle_file: data.subtitle_file,
  });
  
  if (success) {
    editDialogVisible.value = false;
  }
};

// 监听分页变化
watch(currentPage, () => {
  loadVideos();
});

onMounted(() => {
  loadCategories();
  loadVideos();
});
</script>

<style lang="scss" scoped>
.video-center-page {
  min-height: 100vh;
  background: var(--bg-light);
  padding: var(--spacing-lg);
}

.video-list {
  margin-bottom: var(--spacing-lg);
}

.video-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: var(--spacing-lg);
}

.pagination {
  display: flex;
  justify-content: center;
  margin-top: var(--spacing-lg);
}

@media (max-width: 768px) {
  .video-center-page {
    padding: var(--spacing-md);
  }

  .video-grid {
    grid-template-columns: 1fr;
  }
}
</style>
