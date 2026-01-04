<template>
  <div class="bili-creator-center">
    <!-- Header -->
    <UploadHeader />

    <!-- Main Content -->
    <div class="creator-main">
      <!-- Sidebar -->
      <UploadSidebar />

      <!-- Content Area -->
      <div class="creator-content">
        <!-- Breadcrumb -->
        <div class="breadcrumb">
          <span class="breadcrumb-item">全部稿件</span>
          <span class="breadcrumb-separator">></span>
          <span class="breadcrumb-item">已发布</span>
          <span class="breadcrumb-separator">></span>
          <span class="breadcrumb-item current">进行中</span>
        </div>

        <!-- Content Header -->
        <div class="content-header">
          <div class="content-title">
            <h2>稿件管理</h2>
            <div class="title-tabs">
              <div class="title-tab active">全部稿件 1</div>
              <div class="title-tab">进行中 1</div>
              <div class="title-tab">已发布 1</div>
              <div class="title-tab">未通过 0</div>
              <div class="title-tab">已发布 0</div>
              <div class="title-tab">已发布 0</div>
            </div>
          </div>
          <div class="content-actions">
            <button class="action-btn primary" @click="handleUpload">
              <el-icon class="btn-icon"><Upload /></el-icon>
              投稿
            </button>
          </div>
        </div>

        <!-- Filter Bar -->
        <div class="filter-bar">
          <div class="filter-left">
            <select class="filter-select">
              <option>按稿件时间排序</option>
            </select>
          </div>
          <div class="filter-right">
            <div class="view-toggle">
              <button class="toggle-btn active">📋</button>
              <button class="toggle-btn">🔲</button>
            </div>
          </div>
        </div>

        <!-- Video List -->
        <div class="video-list">
          <!-- Upload Modal -->
          <UploadModal
            v-model="showUploadModal"
            :current-step="currentStep"
            :video-file="videoFile"
            :cover-file="coverFile"
            :subtitle-file="subtitleFile"
            :video-preview-url="videoPreviewUrl"
            :cover-preview-url="coverPreviewUrl"
            :has-video-file="hasVideoFile"
            :categories="categories"
            :video-form="videoForm"
            :uploading="uploading"
            :upload-complete="uploadComplete"
            :upload-status="uploadStatus"
            :upload-detail="uploadDetail"
            :total-progress="totalProgress"
            :uploaded-chunks="uploadedChunks"
            :total-chunks="totalChunks"
            :upload-speed="uploadSpeed"
            :remaining-time="remainingTime"
            :cover-progress="coverUploadProgress"
            :subtitle-progress="subtitleUploadProgress"
            :cover-uploading="coverUploading"
            :subtitle-uploading="subtitleUploading"
            ref="uploadModalRef"
            @video-selected="handleVideoSelected"
            @cover-selected="handleCoverSelected"
            @subtitle-selected="handleSubtitleSelected"
            @video-removed="handleVideoRemoved"
            @cover-removed="handleCoverRemoved"
            @subtitle-removed="handleSubtitleRemoved"
            @next-step="nextStep"
            @prev-step="prevStep"
            @start-upload="handleStartUpload"
            @resume-upload="handleResumeUpload"
            @pause-upload="handlePauseUpload"
            @go-home="goToHome"
            @upload-another="uploadAnother"
            @video-form-update="handleVideoFormUpdate"
            @update:modelValue="showUploadModal = $event"
          />

          <!-- Video Item (Placeholder - to be replaced with actual video list) -->
          <div class="video-item" v-if="false">
            <div class="video-cover">
              <img :src="getVideoCoverUrl(undefined)" alt="视频封面" />
              <div class="video-duration">04:33</div>
            </div>
            <div class="video-info">
              <div class="video-title">我的CS不仅会各种特殊大狙，还有神仙队友</div>
              <div class="video-meta">
                <span class="meta-item">2023年09月12日 17:21:05</span>
                <span class="meta-item">审核中 · 公开发布</span>
              </div>
              <div class="video-stats">
                <div class="stat-item">
                  <el-icon class="stat-icon"><View /></el-icon>
                  <span class="stat-value">25</span>
                </div>
                <div class="stat-item">
                  <el-icon class="stat-icon"><ChatDotRound /></el-icon>
                  <span class="stat-value">3</span>
                </div>
                <div class="stat-item">
                  <el-icon class="stat-icon"><CircleCheckFilled /></el-icon>
                  <span class="stat-value">0</span>
                </div>
                <div class="stat-item">
                  <el-icon class="stat-icon"><Star /></el-icon>
                  <span class="stat-value">0</span>
                </div>
                <div class="stat-item">
                  <el-icon class="stat-icon"><Money /></el-icon>
                  <span class="stat-value">1</span>
                </div>
                <div class="stat-item">
                  <el-icon class="stat-icon"><Upload /></el-icon>
                  <span class="stat-value">0</span>
                </div>
              </div>
            </div>
            <div class="video-actions">
              <button class="action-btn-small">编辑</button>
              <button class="action-btn-small more">⋯</button>
            </div>
          </div>

          <!-- Pagination -->
          <div class="pagination">
            <span class="page-info">共1页/1个，跳至</span>
            <input type="number" value="1" class="page-input" />
            <span>页</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { Upload, View, CircleCheckFilled, Star } from "@element-plus/icons-vue";
import UploadHeader from "@/features/video/upload/components/layout/UploadHeader.vue";
import UploadSidebar from "@/features/video/upload/components/layout/UploadSidebar.vue";
import UploadModal from "@/features/video/upload/components/UploadModal.vue";
import { getCategories } from "@/features/video/shared/api/category.api";
import { useFileUpload } from "@/features/video/upload/composables/useFileUpload";
import { useChunkUpload } from "@/features/video/upload/composables/useChunkUpload";
import type { Category } from "@/shared/types/entity";

const router = useRouter();
const currentStep = ref<number>(0);
const showUploadModal = ref<boolean>(false);

// Helper function to get video cover URL
const getVideoCoverUrl = (coverUrl: string | undefined): string => {
  if (!coverUrl) {
    return '/placeholder-cover.png';
  }
  // If coverUrl is already a full URL, return it; otherwise, prepend the API base URL
  if (coverUrl.startsWith('http://') || coverUrl.startsWith('https://')) {
    return coverUrl;
  }
  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || '';
  return `${apiBaseUrl}${coverUrl.startsWith('/') ? '' : '/'}${coverUrl}`;
};

// File upload composable
const {
  videoFile, coverFile, subtitleFile,
  videoPreviewUrl, coverPreviewUrl,
  selectVideoFile, selectCoverFile, selectSubtitleFile,
  removeVideoFile, removeCoverFile, removeSubtitleFile,
  resetFiles,
} = useFileUpload();

// Chunk upload composable
const {
  uploading, uploadComplete, uploadStatus, uploadDetail,
  totalChunks, uploadedChunks, totalProgress,
  uploadSpeed, remainingTime,
  coverUploadProgress, subtitleUploadProgress,
  coverUploading, subtitleUploading,
  startUpload, pauseUpload, resumeUpload, resetUpload,
} = useChunkUpload();

const uploadModalRef = ref<InstanceType<typeof UploadModal> | null>(null);
const videoForm = reactive<{
  title: string;
  description: string;
  category_id: number | null;
}>({ title: "", description: "", category_id: null });

const handleVideoFormUpdate = (value: {
  title: string;
  description: string;
  category_id: number | null;
}) => {
  videoForm.title = value.title ?? "";
  videoForm.description = value.description ?? "";
  videoForm.category_id = value.category_id ?? null;
};

const categories = ref<Category[]>([]);
const hasVideoFile = computed(() => !!videoFile.value);

// Load categories
const loadCategories = async () => {
  try {
    const res = await getCategories();
    if (Array.isArray(res)) {
      categories.value = res;
    } else if (res && res.data) {
      categories.value = res.data as Category[];
    } else {
      categories.value = [];
    }
    if (categories.value.length === 0) {
      ElMessage.warning("暂无可用分类，请联系管理员添加分类");
    }
  } catch (error) {
    console.error("加载分类失败:", error);
    ElMessage.error("加载分类失败，请稍后重试");
    categories.value = [];
  }
};

// Modal handlers
const handleUpload = () => {
  showUploadModal.value = true;
  currentStep.value = 0;
};

const closeUploadModal = () => {
  showUploadModal.value = false;
  resetFiles();
  resetUpload();
  videoForm.title = "";
  videoForm.description = "";
  videoForm.category_id = null;
  currentStep.value = 0;
};

// File handlers
const handleVideoSelected = (file: File) => {
  if (selectVideoFile(file)) {
    if (!videoForm.title) {
      videoForm.title = file.name.replace(/\.[^/.]+$/, "");
    }
  }
};
const handleCoverSelected = (file: File) => selectCoverFile(file);
const handleSubtitleSelected = (file: File) => selectSubtitleFile(file);
const handleVideoRemoved = () => removeVideoFile();
const handleCoverRemoved = () => removeCoverFile();
const handleSubtitleRemoved = () => removeSubtitleFile();

// Step navigation
const nextStep = () => currentStep.value++;
const prevStep = () => currentStep.value--;

// Start upload
const handleStartUpload = async () => {
  if (!videoFile.value) {
    ElMessage.error("请先选择视频文件");
    return;
  }

  let valid = false;
  try {
    if (uploadModalRef.value?.videoFormRef && typeof uploadModalRef.value.videoFormRef.validate === "function") {
      valid = (await uploadModalRef.value.videoFormRef.validate()) ?? false;
    }
  } catch (err) {
    valid = false;
  }

  if (!valid) {
    ElMessage.error("请完善视频信息");
    return;
  }

  if (!videoForm.category_id) {
    ElMessage.error("请选择视频分类");
    return;
  }

  currentStep.value = 2;

  try {
    await startUpload(
      videoFile.value,
      { title: videoForm.title, description: videoForm.description, category_id: videoForm.category_id },
      coverFile.value,
      subtitleFile.value
    );
  } catch (error) {
    console.error("上传失败:", error);
  }
};

const handlePauseUpload = () => pauseUpload();
const handleResumeUpload = async () => {
  if (!videoFile.value || !videoForm.category_id) {
    ElMessage.error("视频文件或分类不存在");
    return;
  }
  try {
    await resumeUpload(
      videoFile.value,
      { title: videoForm.title, description: videoForm.description, category_id: videoForm.category_id },
      coverFile.value,
      subtitleFile.value
    );
  } catch (error) {
    console.error("继续上传失败:", error);
  }
};

const goToHome = () => {
  closeUploadModal();
  router.push("/");
};

const uploadAnother = () => {
  currentStep.value = 0;
  resetFiles();
  resetUpload();
  videoForm.title = "";
  videoForm.description = "";
  videoForm.category_id = null;
};

onMounted(async () => {
  await loadCategories();
});
</script>

<style lang="scss" scoped>
/* B站创作中心样式 */
.bili-creator-center {
  min-height: 100vh;
  background: #f4f5f7;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}


/* Main Content */
.creator-main {
  max-width: 1400px;
  margin: 0 auto;
  display: flex;
  min-height: calc(100vh - 64px);
}


/* Content Area */
.creator-content {
  flex: 1;
  padding: 24px;
  background: #f4f5f7;
}

/* Breadcrumb */
.breadcrumb {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  font-size: 14px;
  color: #61666d;
}

.breadcrumb-item {
  cursor: pointer;
  
  &:hover {
    color: #00aeec;
  }
  
  &.current {
    color: #18191c;
    font-weight: 500;
  }
}

.breadcrumb-separator {
  color: #9499a0;
}

/* Content Header */
.content-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}

.content-title {
  h2 {
    font-size: 24px;
    font-weight: 600;
    color: #18191c;
    margin: 0 0 16px;
  }
}

.title-tabs {
  display: flex;
  gap: 24px;
}

.title-tab {
  padding: 8px 0;
  font-size: 14px;
  color: #61666d;
  cursor: pointer;
  position: relative;
  transition: color 0.2s;
  
  &:hover {
    color: #00aeec;
  }
  
  &.active {
    color: #00aeec;
    font-weight: 500;
    
    &::after {
      content: '';
      position: absolute;
      bottom: -1px;
      left: 0;
      right: 0;
      height: 2px;
      background: #00aeec;
    }
  }
}

.content-actions {
  .action-btn {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 20px;
    border: none;
    border-radius: 6px;
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
    
    &.primary {
      background: #00aeec;
      color: white;
      
      &:hover {
        background: #0099d4;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0, 174, 236, 0.3);
      }
    }
    
    .btn-icon {
      font-size: 16px;
    }
  }
}

/* Filter Bar */
.filter-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
  padding: 16px 20px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.filter-select {
  border: 1px solid #e3e5e7;
  border-radius: 4px;
  padding: 6px 12px;
  font-size: 14px;
  background: white;
  cursor: pointer;
  
  &:focus {
    outline: none;
    border-color: #00aeec;
  }
}

.view-toggle {
  display: flex;
  gap: 4px;
}

.toggle-btn {
  width: 32px;
  height: 32px;
  border: 1px solid #e3e5e7;
  background: white;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
  
  &:hover {
    border-color: #00aeec;
    color: #00aeec;
  }
  
  &.active {
    background: #00aeec;
    border-color: #00aeec;
    color: white;
  }
}

/* Video List */
.video-list {
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.video-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 20px;
  border-bottom: 1px solid #f1f2f3;
  transition: background 0.2s;
  
  &:hover {
    background: #f8f9fa;
  }
  
  &:last-child {
    border-bottom: none;
  }
}

.video-cover {
  position: relative;
  width: 160px;
  height: 90px;
  border-radius: 6px;
  overflow: hidden;
  flex-shrink: 0;
  
  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
  
  .video-duration {
    position: absolute;
    bottom: 4px;
    right: 4px;
    background: rgba(0, 0, 0, 0.8);
    color: white;
    padding: 2px 6px;
    border-radius: 3px;
    font-size: 12px;
  }
}

.video-info {
  flex: 1;
  min-width: 0;
}

.video-title {
  font-size: 16px;
  font-weight: 500;
  color: #18191c;
  margin-bottom: 8px;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.video-meta {
  display: flex;
  gap: 16px;
  margin-bottom: 12px;
  font-size: 13px;
  color: #61666d;
}

.video-stats {
  display: flex;
  gap: 16px;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: #61666d;
  
  .stat-icon {
    font-size: 14px;
  }
}

.video-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.action-btn-small {
  padding: 6px 12px;
  border: 1px solid #e3e5e7;
  background: white;
  border-radius: 4px;
  font-size: 13px;
  color: #61666d;
  cursor: pointer;
  transition: all 0.2s;
  
  &:hover {
    border-color: #00aeec;
    color: #00aeec;
  }
  
  &.more {
    width: 32px;
    padding: 6px;
    display: flex;
    align-items: center;
    justify-content: center;
  }
}

/* Pagination */
.pagination {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 16px 20px;
  font-size: 14px;
  color: #61666d;
  border-top: 1px solid #f1f2f3;
}

.page-input {
  width: 60px;
  padding: 4px 8px;
  border: 1px solid #e3e5e7;
  border-radius: 4px;
  text-align: center;
  font-size: 14px;
  
  &:focus {
    outline: none;
    border-color: #00aeec;
  }
}


/* Responsive */
@media (max-width: 1200px) {
  .creator-main {
    padding: 0;
  }
  
  .creator-content {
    padding: 16px;
  }
}

@media (max-width: 768px) {
  .content-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }
  
  .title-tabs {
    gap: 16px;
    overflow-x: auto;
    padding-bottom: 8px;
  }
  
  .video-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }
  
  .video-cover {
    width: 100%;
    height: auto;
    aspect-ratio: 16/9;
  }
}
</style>
