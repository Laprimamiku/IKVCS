<template>
  <div class="bili-video-center">
    <!-- 顶部导航栏 -->
    <AppHeader />

    <!-- 主内容区 -->
    <main class="main-content">
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
          <div class="stat-card">
            <div class="stat-icon video-icon">📹</div>
            <div class="stat-info">
              <div class="stat-number">{{ total }}</div>
              <div class="stat-label">总视频数</div>
            </div>
          </div>
          <div class="stat-card">
            <div class="stat-icon view-icon">👁️</div>
            <div class="stat-info">
              <div class="stat-number">{{ formatNumber(totalViews) }}</div>
              <div class="stat-label">总播放量</div>
            </div>
          </div>
          <div class="stat-card">
            <div class="stat-icon like-icon">👍</div>
            <div class="stat-info">
              <div class="stat-number">{{ formatNumber(totalLikes) }}</div>
              <div class="stat-label">总点赞数</div>
            </div>
          </div>
          <div class="stat-card">
            <div class="stat-icon comment-icon">💬</div>
            <div class="stat-info">
              <div class="stat-number">{{ formatNumber(totalComments) }}</div>
              <div class="stat-label">总评论数</div>
            </div>
          </div>
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
                <div class="video-status" :class="getStatusClass(video.status)">
                  {{ getStatusText(video.status) }}
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
          <div v-else class="empty-state">
            <div class="empty-icon">📹</div>
            <div class="empty-title">还没有上传视频</div>
            <div class="empty-desc">
              快去上传您的第一个视频吧！
            </div>
            <el-button type="primary" size="large" @click="handleUpload">
              <el-icon><Upload /></el-icon>
              立即上传
            </el-button>
          </div>
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
    </main>

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
import { ref, onMounted, watch, computed } from "vue";
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
} from "@element-plus/icons-vue";
import AppHeader from "@/shared/components/layout/AppHeader.vue";
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
const sortType = ref("newest");

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
.bili-video-center {
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

/* 页面头部 */
.page-header {
  background: #fff;
  border-radius: 8px;
  padding: 24px;
  margin-bottom: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-left {
  .page-title {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 24px;
    font-weight: 600;
    color: #18191c;
    margin: 0 0 8px;
    
    .title-icon {
      font-size: 28px;
      color: #00aeec;
    }
  }
  
  .page-desc {
    font-size: 14px;
    color: #61666d;
  }
}

.header-actions {
  .el-button {
    height: 40px;
    padding: 0 20px;
    border-radius: 20px;
    font-weight: 500;
  }
}

/* 统计卡片 */
.stats-section {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}

.stat-card {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  display: flex;
  align-items: center;
  gap: 16px;
  transition: transform 0.2s;
  
  &:hover {
    transform: translateY(-2px);
  }
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  
  &.video-icon {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  }
  
  &.view-icon {
    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  }
  
  &.like-icon {
    background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
  }
  
  &.comment-icon {
    background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
  }
}

.stat-info {
  .stat-number {
    font-size: 24px;
    font-weight: 600;
    color: #18191c;
    margin-bottom: 4px;
  }
  
  .stat-label {
    font-size: 14px;
    color: #61666d;
  }
}

/* 筛选栏 */
.filter-section {
  background: #fff;
  border-radius: 8px;
  padding: 16px 24px;
  margin-bottom: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
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
  font-size: 14px;
  color: #61666d;
  font-weight: 500;
  flex-shrink: 0;
}

.status-tabs {
  display: flex;
  gap: 4px;
}

.status-tab {
  padding: 6px 16px;
  border-radius: 20px;
  font-size: 14px;
  color: #61666d;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
  
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
  min-height: 400px;
}

/* 加载骨架屏 */
.loading-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
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
      margin-bottom: 8px;
    }
    
    .skeleton-stats {
      height: 12px;
      width: 80%;
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
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
}

.video-card {
  border-radius: 8px;
  overflow: hidden;
  transition: transform 0.2s, box-shadow 0.2s;
  
  &:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
    
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
    bottom: 8px;
    right: 8px;
    background: rgba(0, 0, 0, 0.8);
    color: #fff;
    padding: 2px 6px;
    border-radius: 3px;
    font-size: 12px;
    font-weight: 500;
  }
  
  .video-status {
    position: absolute;
    top: 8px;
    left: 8px;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: 500;
    
    &.published {
      background: #52c41a;
      color: #fff;
    }
    
    &.pending {
      background: #faad14;
      color: #fff;
    }
    
    &.rejected {
      background: #ff4d4f;
      color: #fff;
    }
  }
  
  .video-overlay {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.3);
    display: flex;
    align-items: center;
    justify-content: center;
    opacity: 0;
    transition: opacity 0.3s;
    
    .play-icon {
      font-size: 48px;
      color: #fff;
    }
  }
}

.video-info {
  padding: 16px;
  
  .video-title {
    font-size: 16px;
    font-weight: 500;
    color: #18191c;
    line-height: 1.4;
    margin: 0 0 8px;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    cursor: pointer;
    
    &:hover {
      color: #00aeec;
    }
  }
  
  .video-meta {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;
    font-size: 12px;
    color: #61666d;
    
    .category {
      background: #f1f2f3;
      padding: 2px 6px;
      border-radius: 3px;
    }
  }
  
  .video-stats {
    display: flex;
    align-items: center;
    gap: 16px;
    margin-bottom: 12px;
    font-size: 12px;
    color: #61666d;
    
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

/* 空状态 */
.empty-state {
  text-align: center;
  padding: 80px 20px;
  
  .empty-icon {
    font-size: 80px;
    margin-bottom: 20px;
  }
  
  .empty-title {
    font-size: 20px;
    font-weight: 500;
    color: #18191c;
    margin-bottom: 8px;
  }
  
  .empty-desc {
    font-size: 14px;
    color: #61666d;
    margin-bottom: 24px;
  }
  
  .el-button {
    height: 44px;
    padding: 0 24px;
    border-radius: 22px;
    font-size: 16px;
    font-weight: 500;
  }
}

/* 分页 */
.pagination-section {
  display: flex;
  justify-content: center;
  padding: 24px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
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
</style>