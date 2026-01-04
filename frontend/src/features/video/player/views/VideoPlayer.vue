<template>
  <div class="bili-video-page">
    <AppHeader
      @login="showAuthDialog = true"
      @register="showAuthDialog = true"
    />

    <div class="page-content" v-if="videoData">
      <!-- Main Content Area -->
      <div class="main-section">
        <!-- Player Container -->
        <div class="player-container">
          <div class="player-box">
            <VideoPlayerCore
              ref="playerRef"
              :video-url="videoData.video_url"
              :subtitle-url="videoData.subtitle_url"
              :outline="parsedOutline"
              @timeupdate="handleTimeUpdate"
              @play="handlePlay"
              @playing="handlePlay"
              @pause="handlePause"
              @ended="handlePause"
            />

            <DanmakuDisplay
              :visible="showDanmaku"
              :filter-low-score="filterLowScore"
              :items="danmakuItems"
              :lanes="10"
              :lane-height="28"
              :duration="DANMAKU_DURATION"
              :paused="!isPlaying"
              @finish="finishDanmaku"
            />
          </div>

          <!-- Danmaku Toolbar -->
          <DanmakuToolbar
            v-model:show-danmaku="showDanmaku"
            v-model:filter-low-score="filterLowScore"
            :view-count="videoData.view_count"
            :preset-colors="colorPreset"
            :disabled="!userStore.isLoggedIn"
            :on-send="handleSendDanmaku"
          />
        </div>

        <!-- Video Info Section -->
        <div class="video-info-section">
          <h1 class="video-title">{{ videoData.title }}</h1>
          
          <div class="video-stats">
            <div class="stats-left">
              <span class="stat-item">
                <el-icon><VideoPlay /></el-icon>
                {{ formatNumber(videoData.view_count) }}播放
              </span>
              <span class="stat-item">
                <el-icon><ChatDotRound /></el-icon>
                {{ formatNumber(danmakuItems.length) }}弹幕
              </span>
              <span class="stat-item">
                {{ formatDate(videoData.created_at) }}
              </span>
            </div>
            <div class="stats-right">
              <span class="video-bvid">BV{{ videoData.id }}</span>
            </div>
          </div>

          <!-- Action Buttons (Bilibili Style) -->
          <div class="action-bar">
            <div class="action-item like-btn" :class="{ active: isLiked }" @click="handleLike">
              <div class="action-icon">
                <el-icon :size="20" class="like-icon" :class="{ 'is-liked': isLiked }"><CircleCheckFilled /></el-icon>
              </div>
              <span class="action-text">{{ formatNumber(likeCount) }}</span>
            </div>
            
            <div class="action-item collect-btn" :class="{ active: isCollected }" @click="handleCollectClick">
              <div class="action-icon">
                <el-icon :size="20"><Star /></el-icon>
              </div>
              <span class="action-text">{{ formatNumber(collectCount) }}</span>
            </div>
            
            <div class="action-item share-btn" @click="handleShare">
              <div class="action-icon">
                <el-icon :size="20"><Share /></el-icon>
              </div>
              <span class="action-text">分享</span>
            </div>
            
            <div class="action-item report-btn" @click="handleReport">
              <div class="action-icon">
                <el-icon :size="20"><Warning /></el-icon>
              </div>
              <span class="action-text">举报</span>
            </div>
          </div>

          <!-- Video Description -->
          <div class="video-desc" :class="{ expanded: descExpanded }">
            <div class="desc-content">
              {{ videoData.description || '暂无简介' }}
            </div>
            <div class="desc-toggle" v-if="videoData.description?.length > 100" @click="descExpanded = !descExpanded">
              {{ descExpanded ? '收起' : '展开' }}
              <el-icon><ArrowDown v-if="!descExpanded" /><ArrowUp v-else /></el-icon>
            </div>
          </div>

          <!-- Video Summary -->
          <div class="video-summary-wrapper">
            <VideoSummary
              :video-id="videoData.id"
              :summary-short="videoData.summary_short"
              :summary-detailed="videoData.summary_detailed"
              :knowledge-points="videoData.knowledge_points"
              :show-generate-button="true"
            />
          </div>

          <!-- Tags -->
          <div class="video-tags" v-if="videoData.category">
            <span class="tag">{{ videoData.category.name }}</span>
          </div>
        </div>

        <!-- Comment Section -->
        <div class="comment-section">
          <VideoCommentSection
            :video-id="videoData.id"
            :uploader-id="videoData.uploader.id"
          />
        </div>
      </div>

      <!-- Sidebar -->
      <aside class="sidebar">
        <!-- Uploader Card -->
        <div class="uploader-card">
          <div class="uploader-header">
            <el-avatar :src="videoData.uploader.avatar" :size="48">
              {{ videoData.uploader.nickname?.charAt(0) }}
            </el-avatar>
            <div class="uploader-info">
              <div class="uploader-name">{{ videoData.uploader.nickname }}</div>
              <div class="uploader-fans">{{ formatNumber(videoData.uploader.fans_count || 0) }}粉丝</div>
            </div>
          </div>
          <el-button class="follow-btn" :class="{ followed: isFollowed }" @click="handleFollow">
            {{ isFollowed ? '已关注' : '+ 关注' }}
          </el-button>
        </div>

        <!-- Video Outline -->
        <div class="outline-section">
          <VideoOutline
            :video-id="videoData.id"
            :current-time="currentTime"
            @jump="handleOutlineJump"
          />
        </div>

        <!-- Recommend Videos -->
        <div class="recommend-section">
          <div class="section-title">相关推荐</div>
          <RecommendList
            :videos="recommendVideos"
            @select="handleRecommendClick"
          />
        </div>
      </aside>
    </div>

    <!-- Loading State -->
    <div v-else class="loading-state">
      <div class="loading-player">
        <div class="skeleton-box"></div>
      </div>
      <div class="loading-info">
        <div class="skeleton-title"></div>
        <div class="skeleton-meta"></div>
      </div>
    </div>

    <AuthDialog v-model="showAuthDialog" />
    
    <!-- Collection Folder Dialog -->
    <CollectionFolderDialog 
      v-model="showFolderDialog" 
      @confirm="handleFolderConfirm"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from "vue";
import { useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  VideoPlay,
  ChatDotRound,
  Star,
  Share,
  More,
  ArrowDown,
  ArrowUp,
  CircleCheckFilled,
  Warning,
} from "@element-plus/icons-vue";

import AppHeader from "@/shared/components/layout/AppHeader.vue";
import AuthDialog from "@/features/auth/components/AuthDialog.vue";
import CollectionFolderDialog from "@/features/video/shared/components/CollectionFolderDialog.vue";
import VideoPlayerCore from "@/features/video/player/components/core/VideoPlayerCore.vue";
import DanmakuDisplay from "@/features/video/player/components/danmaku/DanmakuDisplay.vue";
import DanmakuToolbar from "@/features/video/player/components/danmaku/DanmakuToolbar.vue";
import RecommendList from "@/features/video/player/components/recommend/RecommendList.vue";
import VideoCommentSection from "@/features/video/player/components/comment/VideoCommentSection.vue";
import VideoSummary from "@/features/video/player/components/summary/VideoSummary.vue";
import VideoOutline from "@/features/video/player/components/outline/VideoOutline.vue";

import { useUserStore } from "@/shared/stores/user";
import { useVideoPlayer } from "@/features/video/player/composables/useVideoPlayer";
import { useVideoInteractions } from "@/features/video/player/composables/useVideoInteractions";
import { usePlayerState } from "@/features/video/player/composables/usePlayerState";
import {
  useDanmaku,
  DANMAKU_DURATION,
} from "@/features/video/player/composables/useDanmaku";
import { incrementViewCount, getVideoOutline } from "@/features/video/shared/api/video.api";
import type { VideoOutlineEntry } from "@/shared/types/entity";

const router = useRouter();
const userStore = useUserStore();
const showAuthDialog = ref(false);
const showFolderDialog = ref(false);
const showMoreActions = ref(false);
const descExpanded = ref(false);
const isFollowed = ref(false);
const filterLowScore = ref(false);
const hasPlayStarted = ref(false); // 记录是否已经开始播放过

// Video data
const { videoData, recommendVideos, videoIdRef } = useVideoPlayer();

// 视频大纲数据
const outlineData = ref<VideoOutlineEntry[]>([]);

// 解析视频大纲数据（可能是JSON字符串或对象数组）
const parsedOutline = computed<VideoOutlineEntry[]>(() => {
  // 优先使用主动加载的 outline 数据
  if (outlineData.value.length > 0) {
    return outlineData.value;
  }
  
  // 如果没有主动加载的数据，尝试从 videoData 中解析
  if (!videoData.value?.outline) return [];
  
  let outline = videoData.value.outline;
  
  // 如果是字符串，尝试解析为JSON
  if (typeof outline === 'string') {
    try {
      outline = JSON.parse(outline);
    } catch (e) {
      console.error('解析大纲JSON失败:', e);
      return [];
    }
  }
  
  // 确保是数组并按时间排序
  if (Array.isArray(outline)) {
    return outline.sort((a, b) => a.start_time - b.start_time);
  }
  
  return [];
});

// 加载视频大纲
const loadOutline = async () => {
  if (!videoIdRef.value) return;
  
  try {
    const response = await getVideoOutline(videoIdRef.value);
    if (response.success && response.data) {
      let outline = response.data.outline;
      
      // 处理大纲数据（可能是JSON字符串）
      if (typeof outline === 'string') {
        try {
          outline = JSON.parse(outline);
        } catch (e) {
          console.error('解析大纲JSON失败:', e);
          outline = [];
        }
      }
      
      // 确保是数组并按时间排序
      if (Array.isArray(outline)) {
        outlineData.value = outline.sort((a, b) => a.start_time - b.start_time);
      } else {
        outlineData.value = [];
      }
    }
  } catch (error) {
    console.error('加载视频大纲失败:', error);
  }
};

// 监听 videoId 变化，加载大纲
watch(() => videoIdRef.value, () => {
  outlineData.value = [];
  loadOutline();
}, { immediate: true });

// Player state
const {
  currentTime,
  isPlaying,
  showDanmaku,
  handlePlay: originalHandlePlay,
  handlePause,
  handleTimeUpdate,
} = usePlayerState();

// 增强播放处理，首次播放时增加播放量
const handlePlay = async () => {
  originalHandlePlay();
  
  // 只在首次播放时增加播放量
  if (!hasPlayStarted.value && videoIdRef.value) {
    hasPlayStarted.value = true;
    try {
      await incrementViewCount(videoIdRef.value);
      // 更新本地播放量显示
      if (videoData.value) {
        videoData.value.view_count = (videoData.value.view_count || 0) + 1;
      }
    } catch (error) {
      console.warn('播放量统计失败:', error);
    }
  }
};

// Video interactions
const {
  isLiked,
  isCollected,
  likeCount,
  collectCount,
  handleLike,
  handleCollect,
  handleShare,
} = useVideoInteractions(videoData);

// Danmaku system
const {
  activeList: danmakuItems,
  colorPreset,
  send: sendDanmaku,
  finishItem,
} = useDanmaku(videoIdRef, {
  currentUserId: computed(() => userStore.userInfo?.id || null),
  currentTime,
});

// Format helpers
const formatNumber = (num: number): string => {
  if (!num) return "0";
  if (num >= 100000000) return (num / 100000000).toFixed(1) + "亿";
  if (num >= 10000) return (num / 10000).toFixed(1) + "万";
  return num.toString();
};

const formatDate = (dateStr: string): string => {
  if (!dateStr) return "";
  const date = new Date(dateStr);
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
};

// Event handlers
const handleSendDanmaku = async (content: string, color: string) => {
  if (!videoIdRef.value) return false;
  try {
    const res = await sendDanmaku(content, color, currentTime.value);
    return res?.success || false;
  } catch (error) {
    ElMessage.error("发送弹幕失败");
    return false;
  }
};

const finishDanmaku = (key: string) => finishItem(key);

const handleRecommendClick = (id: number) => {
  router.push(`/videos/${id}`);
};

// Handle outline jump
const playerRef = ref<InstanceType<typeof VideoPlayerCore> | null>(null);
const handleOutlineJump = (time: number) => {
  if (playerRef.value) {
    playerRef.value.seek(time);
  }
};

const handleFollow = () => {
  if (!userStore.isLoggedIn) {
    showAuthDialog.value = true;
    return;
  }
  isFollowed.value = !isFollowed.value;
  ElMessage.success(isFollowed.value ? "关注成功" : "已取消关注");
};

// Handle collect click
const handleCollectClick = async () => {
  if (!userStore.isLoggedIn) {
    showAuthDialog.value = true;
    return;
  }
  
  const result = await handleCollect();
  if (result === 'need-folder-selection') {
    // 需要选择文件夹，弹出对话框
    showFolderDialog.value = true;
  }
};

// Handle report
const handleReport = async () => {
  if (!userStore.isLoggedIn) {
    ElMessage.warning("请先登录");
    return;
  }
  
  if (!videoData.value) return;
  
  try {
    const { createReport } = await import('@/features/video/player/api/report.api');
    const res = await ElMessageBox.prompt(
      '请输入举报原因',
      '举报视频',
      {
        confirmButtonText: '提交',
        cancelButtonText: '取消',
        inputPlaceholder: '请简要说明举报原因',
        inputValidator: (value) => {
          if (!value || value.trim().length === 0) return '请输入举报原因';
          if (value.length > 100) return '举报原因不能超过100个字符';
          return true;
        }
      }
    );
    
    const response = await createReport({
      target_type: 'VIDEO',
      target_id: videoData.value.id,
      reason: res.value,
      description: res.value
    });
    
    if (response.success) {
      ElMessage.success(response.data?.message || '举报提交成功');
    } else {
      ElMessage.error('举报提交失败');
    }
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('举报失败:', error);
      ElMessage.error(error?.response?.data?.detail || '举报提交失败');
    }
  }
};

// Handle folder selection confirm
const handleFolderConfirm = async (folderId: number | null) => {
  if (!videoData.value) return;
  
  try {
    const { toggleVideoCollect } = await import('@/features/video/shared/api/video.api');
    const response = await toggleVideoCollect(videoData.value.id, folderId);
    if (response.success && response.data) {
      isCollected.value = response.data.is_collected;
      collectCount.value = response.data.collect_count;
      if (videoData.value) {
        videoData.value.is_collected = response.data.is_collected;
        videoData.value.collect_count = response.data.collect_count;
      }
      window.dispatchEvent(new CustomEvent('video-collect-changed', {
        detail: {
          videoId: videoData.value.id,
          isCollected: response.data.is_collected,
          collectCount: response.data.collect_count
        }
      }));
      ElMessage.success('收藏成功');
    }
  } catch (error) {
    console.error('收藏失败:', error);
    ElMessage.error('收藏失败');
  }
};
</script>

<style lang="scss" scoped>
.bili-video-page {
  min-height: 100vh;
  background: var(--bg-global);
}

.page-content {
  display: grid;
  grid-template-columns: 1fr 350px;
  gap: var(--space-5);
  max-width: 1400px;
  margin: 0 auto;
  padding: var(--space-4) var(--space-5);
}

/* Main Section */
.main-section {
  min-width: 0;
}

/* Player Container - B站风格 */
.player-container {
  background: #000;
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: var(--shadow-lg);
  margin-bottom: var(--space-4);
}

.player-box {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 9;
  background: #000;
}

/* Video Info Section - B站风格 */
.video-info-section {
  background: var(--bg-white);
  border-radius: var(--radius-lg);
  padding: var(--space-5);
  box-shadow: var(--shadow-card);
  margin-bottom: var(--space-4);
}

.video-title {
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
  line-height: 1.3;
  margin: 0 0 var(--space-4);
}

.video-stats {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: var(--space-4);
  margin-bottom: var(--space-4);
  border-bottom: 1px solid var(--divider-color);
  
  .stats-left {
    display: flex;
    align-items: center;
    gap: var(--space-5);
  }
  
  .stat-item {
    display: flex;
    align-items: center;
    gap: var(--space-1);
    color: var(--text-tertiary);
    font-size: var(--font-size-sm);
    
    .el-icon {
      font-size: 16px;
      color: var(--text-quaternary);
    }
  }
  
  .video-bvid {
    color: var(--text-tertiary);
    font-size: var(--font-size-sm);
    cursor: pointer;
    padding: var(--space-1) var(--space-2);
    border-radius: var(--radius-sm);
    transition: var(--transition-fast);
    
    &:hover {
      color: var(--bili-pink);
      background: var(--bili-pink-light);
    }
  }
}

/* Action Bar - B站风格优化 */
.action-bar {
  display: flex;
  align-items: center;
  gap: 0;
  padding: var(--space-4) 0;
  border-bottom: 1px solid var(--divider-color);
}

.action-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-4);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: var(--transition-fast);
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  
  .action-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 36px;
    height: 36px;
    border-radius: var(--radius-circle);
    background: var(--bg-gray-1);
    color: var(--text-secondary);
    transition: var(--transition-base);
  }
  
  .action-text {
    font-size: var(--font-size-sm);
    color: var(--text-secondary);
    font-weight: var(--font-weight-medium);
  }
  
  &:hover {
    background: var(--bg-hover);
    
    .action-icon {
      background: var(--bg-gray-2);
    }
  }
  
  // 点赞按钮特殊样式
  &.like-btn {
    &:hover {
      .action-icon {
        background: var(--bili-pink-light);
        color: var(--bili-pink);
      }
      .action-text {
        color: var(--bili-pink);
      }
    }
    
    &.active {
      .action-icon {
        background: var(--bili-pink);
        color: var(--text-white);
      }
      .action-text {
        color: var(--bili-pink);
      }
    }
    
    .like-icon {
      transition: transform 0.2s, color 0.2s;
      &.is-liked {
        transform: rotate(-15deg) scale(1.1);
        color: var(--bili-pink);
      }
    }
  }
  
  &.report-btn {
    margin-left: auto;
    &:hover {
      .action-icon {
        background: rgba(245, 108, 108, 0.1);
        color: #F56C6C;
      }
      .action-text {
        color: #F56C6C;
      }
    }
  }
  
  // 收藏按钮特殊样式
  &.collect-btn {
    &:hover {
      .action-icon {
        background: var(--warning-light);
        color: var(--warning-color);
      }
      .action-text {
        color: var(--warning-color);
      }
    }
    
    &.active {
      .action-icon {
        background: var(--warning-color);
        color: var(--text-white);
      }
      .action-text {
        color: var(--warning-color);
      }
    }
  }
  
  // 分享按钮特殊样式
  &.share-btn {
    &:hover {
      .action-icon {
        background: var(--bili-blue-light);
        color: var(--bili-blue);
      }
      .action-text {
        color: var(--bili-blue);
      }
    }
  }
  
  // 更多按钮
  &.more-btn {
    margin-left: auto;
    
    .action-icon {
      width: 32px;
      height: 32px;
    }
  }
}

/* Video Description */
.video-desc {
  padding: var(--space-4) 0;
  
  .desc-content {
    font-size: var(--font-size-base);
    color: var(--text-secondary);
    line-height: 1.6;
    max-height: 60px;
    overflow: hidden;
    transition: max-height var(--transition-slow);
  }
  
  &.expanded .desc-content {
    max-height: 500px;
  }
  
  .desc-toggle {
    display: inline-flex;
    align-items: center;
    gap: var(--space-1);
    margin-top: var(--space-2);
    color: var(--bili-blue);
    font-size: var(--font-size-sm);
    cursor: pointer;
    
    &:hover {
      color: var(--bili-pink);
    }
  }
}

/* Video Tags */
.video-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  padding-top: var(--space-3);
  
  .tag {
    padding: var(--space-1) var(--space-3);
    background: var(--bg-gray-1);
    border-radius: var(--radius-round);
    font-size: var(--font-size-xs);
    color: var(--text-secondary);
    cursor: pointer;
    transition: var(--transition-fast);
    
    &:hover {
      background: var(--bili-pink-light);
      color: var(--bili-pink);
    }
  }
}

/* Comment Section */
.comment-section {
  background: var(--bg-white);
  border-radius: var(--radius-lg);
  padding: var(--space-5);
  box-shadow: var(--shadow-card);
}

/* Sidebar */
.sidebar {
  position: sticky;
  top: calc(var(--header-height) + var(--space-4));
  height: fit-content;
}

/* Uploader Card - B站风格 */
.uploader-card {
  background: var(--bg-white);
  border-radius: var(--radius-lg);
  padding: var(--space-5);
  box-shadow: var(--shadow-card);
  margin-bottom: var(--space-4);
  
  .uploader-header {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    margin-bottom: var(--space-4);
  }
  
  .uploader-info {
    flex: 1;
    
    .uploader-name {
      font-size: var(--font-size-lg);
      font-weight: var(--font-weight-semibold);
      color: var(--text-primary);
      margin-bottom: var(--space-1);
      cursor: pointer;
      
      &:hover {
        color: var(--bili-pink);
      }
    }
    
    .uploader-fans {
      font-size: var(--font-size-sm);
      color: var(--text-tertiary);
    }
  }
  
  .follow-btn {
    width: 100%;
    height: 40px;
    background: var(--bili-pink);
    border: none;
    border-radius: var(--radius-md);
    color: var(--text-white);
    font-size: var(--font-size-base);
    font-weight: var(--font-weight-medium);
    cursor: pointer;
    transition: var(--transition-base);
    
    &:hover {
      background: var(--bili-pink-hover);
      transform: translateY(-1px);
      box-shadow: var(--shadow-md);
    }
    
    &.followed {
      background: var(--bg-gray-1);
      color: var(--text-secondary);
      
      &:hover {
        background: var(--bg-gray-2);
        transform: none;
        box-shadow: none;
      }
    }
  }
}

/* Video Summary Wrapper */
.video-summary-wrapper {
  margin: var(--space-4) 0;
}

/* Outline Section */
.outline-section {
  background: var(--bg-white);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
  box-shadow: var(--shadow-card);
  margin-bottom: var(--space-4);
}

/* Recommend Section - B站风格 */
.recommend-section {
  background: var(--bg-white);
  border-radius: var(--radius-lg);
  padding: var(--space-5);
  box-shadow: var(--shadow-card);
  
  .section-title {
    font-size: var(--font-size-lg);
    font-weight: var(--font-weight-semibold);
    color: var(--text-primary);
    margin-bottom: var(--space-4);
    padding-bottom: var(--space-2);
    border-bottom: 2px solid var(--bili-pink);
    position: relative;
    
    &::after {
      content: '';
      position: absolute;
      bottom: -2px;
      left: 0;
      width: 30px;
      height: 2px;
      background: var(--bili-pink);
    }
  }
}

/* Loading State */
.loading-state {
  max-width: 1400px;
  margin: 0 auto;
  padding: var(--space-5) var(--space-6);
  
  .loading-player {
    aspect-ratio: 16 / 9;
    border-radius: var(--radius-lg);
    overflow: hidden;
    
    .skeleton-box {
      width: 100%;
      height: 100%;
      background: linear-gradient(90deg, var(--bg-gray-1) 25%, var(--bg-gray-2) 50%, var(--bg-gray-1) 75%);
      background-size: 200% 100%;
      animation: skeleton-loading 1.5s infinite;
    }
  }
  
  .loading-info {
    background: var(--bg-white);
    border-radius: var(--radius-lg);
    padding: var(--space-5);
    margin-top: var(--space-4);
    
    .skeleton-title {
      height: 24px;
      width: 60%;
      background: linear-gradient(90deg, var(--bg-gray-1) 25%, var(--bg-gray-2) 50%, var(--bg-gray-1) 75%);
      background-size: 200% 100%;
      animation: skeleton-loading 1.5s infinite;
      border-radius: var(--radius-sm);
      margin-bottom: var(--space-3);
    }
    
    .skeleton-meta {
      height: 16px;
      width: 40%;
      background: linear-gradient(90deg, var(--bg-gray-1) 25%, var(--bg-gray-2) 50%, var(--bg-gray-1) 75%);
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

/* Responsive */
@media (max-width: 1100px) {
  .page-content {
    grid-template-columns: 1fr;
    padding: var(--space-3);
  }
  
  .sidebar {
    position: static;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: var(--space-4);
    margin-top: var(--space-4);
  }
  
  .uploader-card {
    margin-bottom: 0;
  }
}

@media (max-width: 768px) {
  .page-content {
    padding: 0;
    gap: 0;
  }
  
  .player-container {
    border-radius: 0;
    margin-bottom: 0;
  }
  
  .video-info-section,
  .comment-section {
    border-radius: 0;
    margin-bottom: 0;
    border-top: 8px solid var(--bg-global);
  }
  
  .sidebar {
    grid-template-columns: 1fr;
    padding: 0;
    margin-top: 0;
  }
  
  .uploader-card,
  .recommend-section {
    border-radius: 0;
    border-top: 8px solid var(--bg-global);
  }
  
  .action-bar {
    flex-wrap: wrap;
    gap: var(--space-2);
    
    .action-item {
      flex: 1;
      min-width: 80px;
      justify-content: center;
      
      &.more-btn {
        flex: none;
        margin-left: 0;
      }
    }
  }
  
  .video-title {
    font-size: var(--font-size-xl);
  }
  
  .video-stats {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--space-2);
    
    .stats-left {
      gap: var(--space-3);
    }
  }
}
</style>
