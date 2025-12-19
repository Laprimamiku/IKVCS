<template>
  <div class="video-player-page">
    <AppHeader
      @login="showAuthDialog = true"
      @register="showAuthDialog = true"
    />

    <div class="main-container" v-if="videoData">
      <!-- 左侧主内容区 -->
      <div class="left-column">
        <!-- 播放器 -->
        <div class="player-wrapper">
          <div class="player-stack">
            <VideoPlayerCore
              ref="playerRef"
              :video-url="videoData.video_url"
              :subtitle-url="videoData.subtitle_url"
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
        </div>

        <!-- 弹幕工具栏 -->
        <DanmakuToolbar
          v-model:show-danmaku="showDanmaku"
          v-model:filter-low-score="filterLowScore"
          :view-count="videoData.view_count"
          :preset-colors="colorPreset"
          :disabled="!userStore.isLoggedIn"
          :on-send="handleSendDanmaku"
        />

        <!-- 视频信息 + 互动 -->
        <VideoInfo
          :video="videoData"
          :danmaku-count="danmakuItems.length"
          :is-liked="isLiked"
          :is-collected="isCollected"
          :like-count="likeCount"
          :collect-count="collectCount"
          @like="handleLike"
          @collect="handleCollect"
          @share="handleShare"
          @report="handleVideoReport"
        />

        <!-- 评论区 -->
        <VideoCommentSection
          :video-id="videoData.id"
          :uploader-id="videoData.uploader.id"
        />
      </div>

      <!-- 右侧推荐区 -->
      <div class="right-column">
        <UploaderCard :uploader="videoData.uploader" @follow="handleFollow" />
        <RecommendList
          :videos="recommendVideos"
          @select="handleRecommendClick"
        />
      </div>
    </div>

    <!-- 加载 / 异常状态 -->
    <div v-else class="loading-container">
      <el-skeleton animated />
    </div>

    <AuthDialog v-model="showAuthDialog" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from "vue";
import { useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";

import AppHeader from "@/shared/components/layout/AppHeader.vue";
import AuthDialog from "@/features/auth/components/AuthDialog.vue";
import VideoPlayerCore from "@/features/video/player/components/core/VideoPlayerCore.vue";
import DanmakuDisplay from "@/features/video/player/components/danmaku/DanmakuDisplay.vue";
import DanmakuToolbar from "@/features/video/player/components/danmaku/DanmakuToolbar.vue";
import VideoInfo from "@/features/video/player/components/info/VideoInfo.vue";
import UploaderCard from "@/features/video/player/components/info/UploaderCard.vue";
import RecommendList from "@/features/video/player/components/recommend/RecommendList.vue";
import VideoCommentSection from "@/features/video/player/components/comment/VideoCommentSection.vue";

import { useUserStore } from "@/shared/stores/user";
import { useVideoPlayer } from "@/features/video/player/composables/useVideoPlayer";
import { useVideoInteractions } from "@/features/video/player/composables/useVideoInteractions";
import { usePlayerState } from "@/features/video/player/composables/usePlayerState";
import {
  useDanmaku,
  DANMAKU_DURATION,
} from "@/features/video/player/composables/useDanmaku";
import { createReport } from "@/features/video/player/api/report.api";

const router = useRouter();
const userStore = useUserStore();
const showAuthDialog = ref(false);

// 弹幕过滤
const filterLowScore = ref(false);

// 1️⃣ 视频数据
const { videoData, recommendVideos, videoIdRef } = useVideoPlayer();

// 2️⃣ 播放器状态
const {
  currentTime,
  isPlaying,
  showDanmaku,
  handlePlay,
  handlePause,
  handleTimeUpdate,
} = usePlayerState();

// 3️⃣ ✅ 视频互动（关键合并点）
const {
  isLiked,
  isCollected,
  likeCount,
  collectCount,
  handleLike,
  handleCollect,
  handleShare,
} = useVideoInteractions(videoData);

// 4️⃣ 弹幕系统
const {
  activeList: danmakuItems,
  colorPreset,
  send: sendDanmaku,
  finishItem,
} = useDanmaku(videoIdRef, {
  currentUserId: computed(() => userStore.userInfo?.id || null),
  currentTime,
});

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

const handleFollow = () => {
  if (!userStore.isLoggedIn) {
    showAuthDialog.value = true;
    return;
  }
  ElMessage.success("关注成功");
};

// 处理视频举报
const handleVideoReport = async () => {
  if (!userStore.isLoggedIn) {
    showAuthDialog.value = true;
    return;
  }
  
  if (!videoData.value) return;
  
  try {
    const { value: reason } = await ElMessageBox.prompt(
      '请输入举报原因',
      '举报视频',
      {
        confirmButtonText: '提交',
        cancelButtonText: '取消',
        inputPlaceholder: '请简要说明举报原因',
        inputValidator: (value) => {
          if (!value || value.trim().length === 0) {
            return '请输入举报原因';
          }
          if (value.length > 100) {
            return '举报原因不能超过100个字符';
          }
          return true;
        }
      }
    );
    
    const res = await createReport({
      target_type: 'VIDEO',
      target_id: videoData.value.id,
      reason: reason.trim(),
    });
    
    if (res.success) {
      ElMessage.success(res.data?.message || '举报提交成功，我们会尽快处理');
    } else {
      ElMessage.error('举报提交失败，请稍后重试');
    }
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('举报失败:', error);
      const errorMsg = error?.response?.data?.detail || error?.message || '举报提交失败，请稍后重试';
      ElMessage.error(errorMsg);
    }
  }
};
</script>

<style lang="scss" scoped>
.video-player-page {
  min-height: 100vh;
  background: var(--bg-global);
  padding-bottom: 40px;
}

.main-container {
  max-width: 1400px;
  margin: 20px auto 0;
  padding: 0 24px;
  display: grid;
  grid-template-columns: 1fr 350px;
  gap: 24px;
  align-items: start;
}

.left-column {
  min-width: 0;
}

.player-wrapper {
  width: 100%;
  aspect-ratio: 16 / 9;
  background: #000;
  position: relative;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
  border-radius: var(--radius-md);
  overflow: hidden;

  .player-stack {
    width: 100%;
    height: 100%;
    position: relative;
  }
}

.loading-container {
  padding: 40px;
  background: var(--bg-white);
  border-radius: var(--radius-md);
  margin: 20px 24px;
}

@media (max-width: 1100px) {
  .main-container {
    grid-template-columns: 1fr;
    padding: 0 16px;
  }

  .right-column {
    margin-top: 20px;
  }
}
</style>
