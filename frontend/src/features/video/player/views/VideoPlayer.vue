<template>
  <div class="video-player-page">
    <AppHeader
      @login="showAuthDialog = true"
      @register="showAuthDialog = true"
    />

    <div class="main-container">
      <!-- 左侧主内容区 -->
      <div class="left-column">
        <!-- 播放器 -->
        <div class="player-wrapper">
          <div class="player-stack">
            <VideoPlayerCore
              ref="playerRef"
              :video-url="videoData?.video_url || null"
              :subtitle-url="videoData?.subtitle_url || null"
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
          :view-count="videoData?.view_count"
          :preset-colors="colorPreset"
          :disabled="!userStore.isLoggedIn"
          :on-send="handleSendDanmaku"
        />

        <!-- 视频信息 -->
        <VideoInfo :video="videoData" :danmaku-count="danmakuItems.length">
          <template #actions>
            <VideoActions
              :is-liked="isLiked"
              :is-collected="isCollected"
              :like-count="videoData?.like_count"
              :collect-count="videoData?.collect_count"
              @like="handleLike"
              @collect="handleCollect"
              @share="handleShare"
            />
          </template>
        </VideoInfo>

        <!-- [New] 评论区 -->
        <VideoCommentSection
          v-if="videoData"
          :video-id="videoData.id"
          :uploader-id="videoData.uploader.id"
        />
      </div>

      <!-- 右侧推荐区 -->
      <div class="right-column">
        <UploaderCard
          :uploader="videoData?.uploader || null"
          @follow="handleFollow"
        />
        <RecommendList
          :videos="recommendVideos"
          @select="handleRecommendClick"
        />
      </div>
    </div>

    <AuthDialog v-model="showAuthDialog" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";

import AppHeader from "@/shared/components/layout/AppHeader.vue";
import AuthDialog from "@/features/auth/components/AuthDialog.vue";
import VideoPlayerCore from "@/features/video/player/components/core/VideoPlayerCore.vue";
import DanmakuDisplay from "@/features/video/player/components/danmaku/DanmakuDisplay.vue";
import DanmakuToolbar from "@/features/video/player/components/danmaku/DanmakuToolbar.vue";
import VideoInfo from "@/features/video/player/components/info/VideoInfo.vue";
import VideoActions from "@/features/video/player/components/info/VideoActions.vue";
import UploaderCard from "@/features/video/player/components/info/UploaderCard.vue";
import RecommendList from "@/features/video/player/components/recommend/RecommendList.vue";

// [New] 评论区组件
import VideoCommentSection from "@/features/video/player/components/comment/VideoCommentSection.vue";

import { useUserStore } from "@/shared/stores/user";
import { useVideoPlayer } from "@/features/video/player/composables/useVideoPlayer";
import { useVideoInteractions } from "@/features/video/player/composables/useVideoInteractions";
import { usePlayerState } from "@/features/video/player/composables/usePlayerState";
import {
  useDanmaku,
  DANMAKU_DURATION,
} from "@/features/video/player/composables/useDanmaku";

const router = useRouter();
const userStore = useUserStore();
const showAuthDialog = ref(false);

// 低分弹幕过滤
const filterLowScore = ref(false);

// 视频数据和推荐
const { videoData, recommendVideos, videoIdRef } = useVideoPlayer();

// 播放器状态
const {
  currentTime,
  isPlaying,
  showDanmaku,
  handlePlay,
  handlePause,
  handleTimeUpdate,
} = usePlayerState();

// 视频交互
const { isLiked, isCollected, handleLike, handleCollect, handleShare } =
  useVideoInteractions();

// 弹幕
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
    console.error("发送弹幕失败", error);
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
</script>

<style lang="scss" scoped>
.video-player-page {
  min-height: 100vh;
  background: #f6f7f8;
  padding-bottom: 40px;
}

.main-container {
  max-width: 1400px;
  margin: 20px auto 0;
  padding: 0 20px;
  display: grid;
  grid-template-columns: 1fr 350px;
  gap: 30px;
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
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  border-radius: 4px;
  overflow: hidden;

  .player-stack {
    width: 100%;
    height: 100%;
    position: relative;
  }
}

@media (max-width: 1100px) {
  .main-container {
    grid-template-columns: 1fr;
  }

  .right-column {
    margin-top: 20px;
  }
}
</style>
