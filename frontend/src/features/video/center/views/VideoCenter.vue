<template>
  <div class="bili-creator-center">
    <!-- 顶部导航栏 -->
    <AppHeader />

    <!-- 主内容区 -->
    <main class="creator-main">
      <!-- 侧边栏 -->
      <CreatorSidebar :active-tab="activeTab" @tab-change="handleTabChange" />

      <!-- 内容区域 -->
      <div class="creator-content">
        <!-- 视频管理 -->
        <div v-if="activeTab === 'videos'" class="tab-content">
          <div class="content-container">
        <!-- 页面头部 -->
        <div class="page-header">
          <div class="header-left">
            <h1 class="page-title">
              <el-icon class="title-icon"><VideoCamera /></el-icon>
              我的视频
            </h1>
            <div class="page-desc">管理您上传的所有视频内容</div>
          </div>
          <div class="header-actions">
            <el-button type="primary" size="large" @click="handleUpload">
              <el-icon><Upload /></el-icon>
              上传视频
            </el-button>
          </div>
        </div>

        <!-- 统计卡片 -->
        <div class="stats-section">
          <StatCard :value="total" label="总视频数" variant="primary">
            <template #icon>
              <el-icon><VideoCamera /></el-icon>
            </template>
          </StatCard>
          <StatCard :value="formatNumber(totalViews)" label="总播放量" variant="success">
            <template #icon>
              <el-icon><View /></el-icon>
            </template>
          </StatCard>
          <StatCard :value="formatNumber(totalLikes)" label="总点赞数" variant="warning">
            <template #icon>
              <el-icon><Like /></el-icon>
            </template>
          </StatCard>
          <StatCard :value="formatNumber(totalComments)" label="总评论数" variant="default">
            <template #icon>
              <el-icon><ChatDotRound /></el-icon>
            </template>
          </StatCard>
        </div>

        <!-- 筛选栏 -->
        <div class="filter-section">
          <div class="filter-left">
            <div class="filter-group">
              <span class="filter-label">状态筛选：</span>
              <div class="status-tabs">
                <div 
                  class="status-tab" 
                  :class="{ active: statusFilter === null }"
                  @click="handleStatusChange(null)"
                >
                  全部 ({{ total }})
                </div>
                <div 
                  class="status-tab" 
                  :class="{ active: statusFilter === 1 }"
                  @click="handleStatusChange(1)"
                >
                  已发布 ({{ publishedCount }})
                </div>
                <div 
                  class="status-tab" 
                  :class="{ active: statusFilter === 0 }"
                  @click="handleStatusChange(0)"
                >
                  审核中 ({{ pendingCount }})
                </div>
                <div 
                  class="status-tab" 
                  :class="{ active: statusFilter === -1 }"
                  @click="handleStatusChange(-1)"
                >
                  未通过 ({{ rejectedCount }})
                </div>
              </div>
            </div>
          </div>
          <div class="filter-right">
            <el-select v-model="sortType" placeholder="排序方式" style="width: 140px">
              <el-option label="最新上传" value="newest" />
              <el-option label="最多播放" value="popular" />
              <el-option label="最多点赞" value="liked" />
            </el-select>
          </div>
        </div>

        <!-- 视频列表 -->
        <div class="video-section">
          <!-- 加载状态 -->
          <div v-if="loading && videos.length === 0" class="loading-grid">
            <div v-for="i in 6" :key="i" class="video-skeleton">
              <div class="skeleton-cover"></div>
              <div class="skeleton-info">
                <div class="skeleton-title"></div>
                <div class="skeleton-meta"></div>
                <div class="skeleton-stats"></div>
              </div>
            </div>
          </div>

          <!-- 视频网格 -->
          <div v-else-if="videos.length > 0" class="video-grid">
            <div 
              v-for="video in videos" 
              :key="video.id"
              class="video-card"
            >
              <div class="video-cover" @click="handleView(video.id)">
                <img :src="video.cover_url || '/placeholder-video.jpg'" :alt="video.title" />
                <div class="video-duration">{{ formatDuration(video.duration) }}</div>
                <div class="video-status" :class="getStatusClass(video.status || 0)">
                  {{ getStatusText(video.status || 0) }}
                </div>
                <div class="video-overlay">
                  <el-icon class="play-icon"><VideoPlay /></el-icon>
                </div>
              </div>
              
              <div class="video-info">
                <h3 class="video-title" @click="handleView(video.id)">{{ video.title }}</h3>
                <div class="video-meta">
                  <span class="upload-time">{{ formatTime(video.created_at) }}</span>
                  <span class="category" v-if="video.category">{{ video.category.name }}</span>
                  
                  <!-- AI Inference Tag -->
                  <InferenceEngineTag :result="video.ai_analysis_result" />
                </div>
                
                <div class="video-stats">
                  <div class="stat-item">
                    <el-icon><VideoPlay /></el-icon>
                    <span>{{ formatNumber(video.view_count || 0) }}</span>
                  </div>
                  <div class="stat-item">
                    <el-icon><ChatDotRound /></el-icon>
                    <span>{{ formatNumber(video.comment_count || 0) }}</span>
                  </div>
                  <div class="stat-item">
                    <el-icon><Star /></el-icon>
                    <span>{{ formatNumber(video.like_count || 0) }}</span>
                  </div>
                </div>
                
                <div class="video-actions">
                  <el-button size="small" @click="handleAnalyze(video)">
                    <el-icon><DataAnalysis /></el-icon>
                    智能分析
                  </el-button>
                  <el-button size="small" @click="handleEdit(video)">
                    <el-icon><Edit /></el-icon>
                    编辑
                  </el-button>
                  <el-button size="small" @click="handleView(video.id)">
                    <el-icon><View /></el-icon>
                    查看
                  </el-button>
                  <el-dropdown @command="(command) => handleAction(command, video)">
                    <el-button size="small">
                      <el-icon><More /></el-icon>
                    </el-button>
                    <template #dropdown>
                      <el-dropdown-menu>
                        <el-dropdown-item command="share">分享</el-dropdown-item>
                        <el-dropdown-item command="download">下载</el-dropdown-item>
                        <el-dropdown-item command="delete" divided>删除</el-dropdown-item>
                      </el-dropdown-menu>
                    </template>
                  </el-dropdown>
                </div>
              </div>
            </div>
          </div>

          <!-- 空状态 -->
          <EmptyState
            v-if="!loading && videos.length === 0"
            title="还没有上传视频"
            description="快去上传您的第一个视频吧！"
            :icon="VideoCamera"
            :icon-size="64"
          >
            <template #action>
              <el-button type="primary" size="large" @click="handleUpload">
                <el-icon><Upload /></el-icon>
                立即上传
              </el-button>
            </template>
          </EmptyState>
        </div>

        <!-- 分页 -->
        <div v-if="total > pageSize" class="pagination-section">
          <el-pagination
            v-model:current-page="currentPage"
            :page-size="pageSize"
            :total="total"
            layout="total, prev, pager, next, jumper"
            @current-change="loadVideos"
          />
        </div>
          </div>
        </div>

        <!-- 数据中心 -->
        <div v-if="activeTab === 'data'" class="tab-content">
          <CreatorDataCenter :videos="videos" />
        </div>

        <!-- 互动管理 -->
        <div v-if="activeTab === 'interaction'" class="tab-content">
          <CreatorInteraction :videos="videos" />
        </div>
      </div>
    </main>

    <!-- 编辑对话框 -->
    <VideoEditDialog
      v-model="editDialogVisible"
      :video="editingVideo"
      :categories="categories"
      @save="handleSaveEdit"
      @cancel="editDialogVisible = false"
    />

    <!-- 上传模态框 -->
    <el-dialog
      v-model="showUploadModal"
      title="视频投稿"
      width="900px"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      @close="closeUploadModal"
    >
      <!-- Steps Indicator -->
      <div class="upload-steps">
        <div class="steps-bar">
          <div 
            class="step-item" 
            :class="{ active: currentStep >= 0, completed: currentStep > 0 }"
          >
            <div class="step-circle">
              <span v-if="currentStep > 0">✓</span>
              <span v-else>1</span>
            </div>
            <span class="step-label">选择文件</span>
          </div>
          <div class="step-line" :class="{ active: currentStep > 0 }"></div>
          <div 
            class="step-item" 
            :class="{ active: currentStep >= 1, completed: currentStep > 1 }"
          >
            <div class="step-circle">
              <span v-if="currentStep > 1">✓</span>
              <span v-else>2</span>
            </div>
            <span class="step-label">填写信息</span>
          </div>
          <div class="step-line" :class="{ active: currentStep > 1 }"></div>
          <div 
            class="step-item" 
            :class="{ active: currentStep >= 2, completed: uploadComplete }"
          >
            <div class="step-circle">
              <span v-if="uploadComplete">✓</span>
              <span v-else>3</span>
            </div>
            <span class="step-label">上传完成</span>
          </div>
        </div>
      </div>

      <!-- Step Content -->
      <div class="upload-step-content">
        <!-- Step 1: File Selection -->
        <div v-show="currentStep === 0" class="upload-step">
          <FileSelector
            :video-file="videoFile"
            :cover-file="coverFile"
            :subtitle-file="subtitleFile"
            :video-preview-url="videoPreviewUrl"
            :cover-preview-url="coverPreviewUrl"
            @video-selected="handleVideoSelected"
            @cover-selected="handleCoverSelected"
            @subtitle-selected="handleSubtitleSelected"
            @video-removed="handleVideoRemoved"
            @cover-removed="handleCoverRemoved"
            @subtitle-removed="handleSubtitleRemoved"
          />
          <div class="step-actions">
            <el-button
              type="primary"
              size="large"
              :disabled="!hasVideoFile"
              @click="nextStep"
            >
              下一步
            </el-button>
          </div>
        </div>

        <!-- Step 2: Video Info -->
        <div v-show="currentStep === 1" class="upload-step">
          <VideoInfoForm
            ref="videoFormRef"
            :categories="uploadCategories"
            :model-value="videoForm"
            @update:modelValue="handleVideoFormUpdate"
          />
          <div class="step-actions">
            <el-button size="large" @click="prevStep">上一步</el-button>
            <el-button
              type="primary"
              size="large"
              :loading="uploading"
              @click="handleStartUpload"
            >
              开始上传
            </el-button>
          </div>
        </div>

        <!-- Step 3: Upload Progress -->
        <div v-show="currentStep === 2" class="upload-step">
          <UploadProgress
            :status="uploadStatus"
            :detail="uploadDetail"
            :progress="totalProgress"
            :complete="uploadComplete"
            :uploading="uploading"
            :uploaded-chunks="uploadedChunks"
            :total-chunks="totalChunks"
            :speed="uploadSpeed"
            :remaining-time="remainingTime"
            @resume="handleResumeUpload"
            @pause="handlePauseUpload"
            @go-home="goToHome"
            @upload-another="uploadAnother"
          />
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, watch, computed } from "vue";
import { useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  VideoCamera,
  Upload,
  VideoPlay,
  ChatDotRound,
  Star,
  Edit,
  View,
  More,
  Lightning,
  Cloudy,
  DataAnalysis,
} from "@element-plus/icons-vue";
import AppHeader from "@/shared/components/layout/AppHeader.vue";
import StatCard from "@/shared/components/atoms/StatCard.vue";
import EmptyState from "@/shared/components/atoms/EmptyState.vue";
import VideoEditDialog from "@/features/video/center/components/VideoEditDialog.vue";
import InferenceEngineTag from "@/features/video/center/components/InferenceEngineTag.vue";
import CreatorSidebar from "@/features/video/center/components/CreatorSidebar.vue";
import CreatorDataCenter from "@/features/video/center/views/CreatorDataCenter.vue";
import CreatorInteraction from "@/features/video/center/views/CreatorInteraction.vue";
import FileSelector from "@/features/video/upload/components/FileSelector.vue";
import VideoInfoForm from "@/features/video/upload/components/VideoInfoForm.vue";
import UploadProgress from "@/features/video/upload/components/UploadProgress.vue";
import { useVideoManagement } from "@/features/video/center/composables/useVideoManagement";
import { useFileUpload } from "@/features/video/upload/composables/useFileUpload";
import { useChunkUpload } from "@/features/video/upload/composables/useChunkUpload";
import { getCategories } from "@/features/video/shared/api/category.api";
import { formatNumber } from "@/shared/utils/formatters";
import type { Video, Category } from "@/shared/types/entity";

const router = useRouter();

// 标签页管理
const activeTab = ref<'videos' | 'data' | 'interaction'>('videos');
const handleTabChange = (tab: 'videos' | 'data' | 'interaction') => {
  activeTab.value = tab;
};

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
const sortType = ref("newest");

// 上传相关状态
const showUploadModal = ref(false);
const currentStep = ref(0);
const uploadCategories = ref<Category[]>([]);
const videoFormRef = ref<InstanceType<typeof VideoInfoForm> | null>(null);
const videoForm = reactive<{
  title: string;
  description: string;
  category_id: number | null;
}>({ title: "", description: "", category_id: null });

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
  startUpload, pauseUpload, resumeUpload, resetUpload,
} = useChunkUpload();

const hasVideoFile = computed(() => !!videoFile.value);

// 统计数据
const totalViews = computed(() => {
  return videos.value.reduce((sum, video) => sum + (video.view_count || 0), 0);
});

const totalLikes = computed(() => {
  return videos.value.reduce((sum, video) => sum + (video.like_count || 0), 0);
});

const totalComments = computed(() => {
  return videos.value.reduce((sum, video) => sum + (video.comment_count || 0), 0);
});

const publishedCount = computed(() => {
  return videos.value.filter(video => video.status === 1).length;
});

const pendingCount = computed(() => {
  return videos.value.filter(video => video.status === 0).length;
});

const rejectedCount = computed(() => {
  return videos.value.filter(video => video.status === -1).length;
});

/**
 * 格式化数字
 */
// formatNumber 已从 @/shared/utils/formatters 导入

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
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
};

/**
 * 获取状态样式类
 */
const getStatusClass = (status: number): string => {
  switch (status) {
    case 1: return 'published';
    case 0: return 'pending';
    case -1: return 'rejected';
    default: return 'unknown';
  }
};

/**
 * 获取状态文本
 */
const getStatusText = (status: number): string => {
  switch (status) {
    case 1: return '已发布';
    case 0: return '审核中';
    case -1: return '未通过';
    default: return '未知';
  }
};

// 操作处理
const handleUpload = async () => {
  showUploadModal.value = true;
  currentStep.value = 0;
  // 加载分类（如果还没有加载）
  if (uploadCategories.value.length === 0) {
    await loadUploadCategories();
  }
};

// 加载上传分类
const loadUploadCategories = async () => {
  try {
    const res = await getCategories();
    if (Array.isArray(res)) {
      uploadCategories.value = res;
    } else if (res && res.data) {
      uploadCategories.value = res.data as Category[];
    } else {
      uploadCategories.value = [];
    }
  } catch (error) {
    console.error("加载分类失败:", error);
    ElMessage.error("加载分类失败，请稍后重试");
    uploadCategories.value = [];
  }
};

// 关闭上传模态框
const closeUploadModal = () => {
  showUploadModal.value = false;
  resetFiles();
  resetUpload();
  videoForm.title = "";
  videoForm.description = "";
  videoForm.category_id = null;
  currentStep.value = 0;
};

// 文件处理
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

// 步骤导航
const nextStep = () => currentStep.value++;
const prevStep = () => currentStep.value--;

// 视频表单更新
const handleVideoFormUpdate = (value: {
  title: string;
  description: string;
  category_id: number | null;
}) => {
  videoForm.title = value.title ?? "";
  videoForm.description = value.description ?? "";
  videoForm.category_id = value.category_id ?? null;
};

// 开始上传
const handleStartUpload = async () => {
  if (!videoFile.value) {
    ElMessage.error("请先选择视频文件");
    return;
  }

  let valid = false;
  try {
    if (videoFormRef.value && typeof videoFormRef.value.validate === "function") {
      valid = (await videoFormRef.value.validate()) ?? false;
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
    // 上传完成后刷新视频列表
    if (uploadComplete.value) {
      await loadVideos();
    }
  } catch (error) {
    console.error("上传失败:", error);
    ElMessage.error("上传失败，请稍后重试");
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
    ElMessage.error("继续上传失败，请稍后重试");
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

const handleView = (videoId: number) => {
  viewVideo(videoId);
};

const handleAnalyze = (video: Video) => {
  router.push(`/center/analysis/${video.id}`);
};

const handleEdit = (video: Video) => {
  editingVideo.value = video;
  editDialogVisible.value = true;
};

const handleAction = async (command: string, video: Video) => {
  switch (command) {
    case 'share':
      // 分享功能
      ElMessage.info('分享功能开发中');
      break;
    case 'download':
      // 下载功能
      ElMessage.info('下载功能开发中');
      break;
    case 'delete':
      await handleDelete(video);
      break;
  }
};

const handleDelete = async (video: Video) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除视频"${video.title}"吗？此操作不可恢复。`,
      '删除确认',
      {
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        type: 'warning',
      }
    );
    await deleteVideoItem(video);
  } catch (error) {
    // 用户取消删除
  }
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
.bili-creator-center {
  min-height: 100vh;
  background: var(--bg-global);
}

.creator-main {
  display: flex;
  min-height: calc(100vh - var(--header-height));
}

.creator-content {
  flex: 1;
  padding: var(--space-6);
  overflow-y: auto;
}

.tab-content {
  width: 100%;
}

.content-container {
  max-width: 1400px;
  margin: 0 auto;
}

.content-container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 var(--space-5);
}

/* 页面头部 */
.page-header {
  background: var(--bg-white);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
  margin-bottom: var(--space-5);
  box-shadow: var(--shadow-card);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-left {
  .page-title {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    font-size: var(--font-size-3xl);
    font-weight: var(--font-weight-semibold);
    color: var(--text-primary);
    margin: 0 0 var(--space-2);
    
    .title-icon {
      font-size: var(--font-size-4xl);
      color: var(--bili-blue);
    }
  }
  
  .page-desc {
    font-size: var(--font-size-base);
    color: var(--text-secondary);
  }
}

.header-actions {
  .el-button {
    height: var(--btn-height-xl);
    padding: 0 var(--space-5);
    border-radius: var(--radius-round);
    font-weight: var(--font-weight-medium);
  }
}

/* 统计卡片 */
.stats-section {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--space-4);
  margin-bottom: var(--space-5);
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-circle);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  color: var(--text-white);
  
  &.video-icon {
    background: var(--bili-pink-gradient);
  }
  
  &.view-icon {
    background: linear-gradient(135deg, var(--bili-blue) 0%, var(--bili-blue-hover) 100%);
  }
  
  &.like-icon {
    background: linear-gradient(135deg, #FF6B6B 0%, #FF8E8E 100%);
  }
  
  &.comment-icon {
    background: linear-gradient(135deg, var(--success-color) 0%, #52C41A 100%);
  }
}

.stat-info {
  .stat-number {
    font-size: var(--font-size-2xl);
    font-weight: var(--font-weight-semibold);
    color: var(--text-primary);
    margin-bottom: var(--space-1);
  }
  
  .stat-label {
    font-size: var(--font-size-sm);
    color: var(--text-secondary);
  }
}

/* 筛选栏 */
.filter-section {
  background: var(--bg-white);
  border-radius: var(--radius-lg);
  padding: var(--space-4) var(--space-6);
  margin-bottom: var(--space-5);
  box-shadow: var(--shadow-card);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 12px;
}

.filter-label {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  font-weight: var(--font-weight-medium);
  flex-shrink: 0;
}

.status-tabs {
  display: flex;
  gap: 4px;
}

.status-tab {
  padding: var(--space-1) var(--space-4);
  border-radius: var(--radius-round);
  font-size: var(--font-size-base);
  color: var(--text-secondary);
  cursor: pointer;
  transition: var(--transition-base);
  white-space: nowrap;
  
  &:hover {
    background: var(--bg-hover);
    color: var(--text-primary);
  }
  
  &.active {
    background: var(--bili-blue);
    color: var(--text-white);
  }
}

/* 视频区域 */
.video-section {
  background: var(--bg-white);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
  box-shadow: var(--shadow-card);
  margin-bottom: var(--space-5);
  min-height: 400px;
}

/* 加载骨架屏 */
.loading-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: var(--space-5);
}

.video-skeleton {
  .skeleton-cover {
    width: 100%;
    aspect-ratio: 16/9;
    background: linear-gradient(
      90deg,
      var(--bg-gray-1) 25%,
      var(--bg-gray-2) 50%,
      var(--bg-gray-1) 75%
    );
    background-size: 200% 100%;
    animation: skeleton-loading 1.5s infinite;
    border-radius: var(--radius-md);
    margin-bottom: var(--space-3);
  }
  
  .skeleton-info {
    .skeleton-title {
      height: var(--font-size-lg);
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
      margin-bottom: var(--space-2);
    }
    
    .skeleton-stats {
      height: var(--font-size-sm);
      width: 80%;
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
}

@keyframes skeleton-loading {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* 视频网格 */
.video-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: var(--space-5);
}

.video-card {
  border-radius: var(--radius-lg);
  overflow: hidden;
  transition: var(--transition-base);
  
  &:hover {
    transform: translateY(-4px);
    box-shadow: var(--shadow-card-hover);
    
    .video-overlay {
      opacity: 1;
    }
    
    .video-cover img {
      transform: scale(1.05);
    }
  }
}

.video-cover {
  position: relative;
  width: 100%;
  aspect-ratio: 16/9;
  overflow: hidden;
  cursor: pointer;
  
  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    transition: transform 0.3s;
  }
  
  .video-duration {
    position: absolute;
    bottom: var(--space-2);
    right: var(--space-2);
    background: var(--bg-mask);
    color: var(--text-white);
    padding: var(--space-1) var(--space-1);
    border-radius: var(--radius-sm);
    font-size: var(--font-size-xs);
    font-weight: var(--font-weight-medium);
  }
  
  .video-status {
    position: absolute;
    top: var(--space-2);
    left: var(--space-2);
    padding: var(--space-1) var(--space-2);
    border-radius: var(--radius-round);
    font-size: var(--font-size-xs);
    font-weight: var(--font-weight-medium);
    
    &.published {
      background: var(--success-color);
      color: var(--text-white);
    }
    
    &.pending {
      background: var(--warning-color);
      color: var(--text-white);
    }
    
    &.rejected {
      background: var(--danger-color);
      color: var(--text-white);
    }
  }
  
  .video-overlay {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: var(--bg-mask-light);
    display: flex;
    align-items: center;
    justify-content: center;
    opacity: 0;
    transition: opacity var(--transition-slow);
    
    .play-icon {
      font-size: var(--font-size-5xl);
      color: var(--text-white);
    }
  }
}

.video-info {
  padding: var(--space-4);
  
  .video-title {
    font-size: var(--font-size-md);
    font-weight: var(--font-weight-medium);
    color: var(--text-primary);
    line-height: var(--line-height-normal);
    margin: 0 0 var(--space-2);
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    cursor: pointer;
    
    &:hover {
      color: var(--bili-blue);
    }
  }
  
  .video-meta {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: var(--space-3);
    font-size: var(--font-size-xs);
    color: var(--text-secondary);
    
    .category {
      background: var(--bg-gray-1);
      padding: var(--space-1) var(--space-1);
      border-radius: var(--radius-sm);
    }

    .ai-tag {
      display: flex;
      align-items: center;
      gap: var(--space-1);
      padding: var(--space-1) var(--space-1);
      border-radius: var(--radius-sm);
      font-size: 11px;
      font-weight: var(--font-weight-medium);
      cursor: help;
      margin-left: var(--space-2);
      
      &.local {
        background: var(--success-light);
        color: var(--success-color);
        border: 1px solid var(--success-color);
      }
      
      &.cloud {
        background: var(--info-light);
        color: var(--info-color);
        border: 1px solid var(--info-color);
      }
    }
  }
  
  .video-stats {
    display: flex;
    align-items: center;
    gap: var(--space-4);
    margin-bottom: var(--space-3);
    font-size: var(--font-size-xs);
    color: var(--text-secondary);
    
    .stat-item {
      display: flex;
      align-items: center;
      gap: 4px;
      
      .el-icon {
        font-size: 12px;
      }
    }
  }
  
  .video-actions {
    display: flex;
    gap: 8px;
    
    .el-button {
      flex: 1;
      height: 32px;
      font-size: 12px;
    }
  }
}

/* 分页 */
.pagination-section {
  display: flex;
  justify-content: center;
  padding: var(--space-6);
  background: var(--bg-white);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-card);
}

/* 响应式 */
@media (max-width: 1200px) {
  .content-container {
    padding: 0 16px;
  }
  
  .video-grid {
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 16px;
  }
  
  .loading-grid {
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 16px;
  }
}

@media (max-width: 768px) {
  .content-container {
    padding: 0 12px;
  }
  
  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
    padding: 16px;
  }
  
  .stats-section {
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
  }
  
  .stat-card {
    padding: 16px;
  }
  
  .filter-section {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
    padding: 16px;
  }
  
  .status-tabs {
    flex-wrap: wrap;
    gap: 8px;
  }
  
  .video-section {
    padding: 16px;
  }
  
  .video-grid {
    grid-template-columns: 1fr;
    gap: 16px;
  }
  
  .loading-grid {
    grid-template-columns: 1fr;
    gap: 16px;
  }
}

@media (max-width: 480px) {
  .stats-section {
    grid-template-columns: 1fr;
  }
  
  .stat-card {
    padding: 12px;
  }
  
  .stat-icon {
    width: 40px;
    height: 40px;
    font-size: 20px;
  }
  
  .stat-info .stat-number {
    font-size: 20px;
  }
}

/* Upload Modal Styles */
:deep(.el-dialog__body) {
  padding: var(--space-6);
}

.upload-steps {
  margin-bottom: var(--space-8);
}

.steps-bar {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0;
}

.step-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
  
  &.active {
    .step-circle {
      background: var(--bili-blue);
      color: var(--text-white);
      box-shadow: var(--shadow-md);
    }
    
    .step-label {
      color: var(--bili-blue);
      font-weight: var(--font-weight-medium);
    }
  }
  
  &.completed {
    .step-circle {
      background: var(--success-color);
      color: var(--text-white);
    }
    
    .step-label {
      color: var(--success-color);
    }
  }
}

.step-circle {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-circle);
  background: var(--bg-gray-1);
  color: var(--text-tertiary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  transition: all var(--transition-base);
}

.step-label {
  font-size: var(--font-size-sm);
  color: var(--text-tertiary);
  transition: color var(--transition-base);
}

.step-line {
  width: 80px;
  height: 2px;
  background: var(--bg-gray-1);
  margin: 0 var(--space-4);
  margin-bottom: var(--space-6);
  border-radius: 1px;
  transition: background var(--transition-base);

  &.active {
    background: var(--bili-blue);
  }
}

.upload-step-content {
  animation: fadeIn 0.3s ease-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.upload-step {
  min-height: 400px;
  display: flex;
  flex-direction: column;
}

.step-actions {
  display: flex;
  justify-content: center;
  gap: var(--space-4);
  margin-top: auto;
  padding-top: var(--space-6);
  border-top: 1px solid var(--border-light);
}
</style>