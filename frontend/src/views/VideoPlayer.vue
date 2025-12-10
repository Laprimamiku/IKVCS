<template>
  <div class="video-player-page">
    <!-- 顶部导航栏 -->
    <AppHeader @login="showAuthDialog = true" @register="showAuthDialog = true" />

    <div class="player-container">
      <!-- 左侧：视频播放器和信息 -->
      <div class="main-content">
        <!-- 视频播放器 -->
        <div class="player-wrapper">
          <VideoPlayerCore
            :video-url="videoData?.video_url || null"
            :subtitle-url="videoData?.subtitle_url || null"
          />
        </div>

        <!-- 视频信息 -->
        <div class="video-info-wrapper">
          <VideoInfo :video-data="videoData" />
          <VideoActions
            :video-data="videoData"
            :is-liked="isLiked"
            :is-collected="isCollected"
            @like="handleLike"
            @collect="handleCollect"
            @share="handleShare"
          />
        </div>
      </div>

      <!-- 右侧：推荐视频 -->
      <div class="sidebar-content">
        <h3 class="sidebar-title">推荐视频</h3>
        <div class="recommend-list">
          <div
            v-for="video in recommendVideos"
            :key="video.id"
            class="recommend-item"
            @click="$router.push(`/videos/${video.id}`)"
          >
            <img :src="getCoverUrl(video.cover)" :alt="video.title" class="recommend-cover" />
            <div class="recommend-info">
              <div class="recommend-title">{{ video.title }}</div>
              <div class="recommend-meta">
                <span>{{ video.uploader }}</span>
                <span>{{ video.views }} 播放</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 加载状态 -->
    <el-skeleton v-if="loading" animated class="content-container">
      <template #template>
        <el-skeleton-item variant="h1" style="width: 60%" />
        <el-skeleton-item variant="text" style="width: 40%; margin-top: 16px" />
        <el-skeleton-item variant="rect" style="height: 100px; margin-top: 24px" />
      </template>
    </el-skeleton>

    <!-- 登录对话框 -->
    <AuthDialog v-model="showAuthDialog" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import AppHeader from "@/components/layout/AppHeader.vue";
import AuthDialog from "@/components/AuthDialog.vue";
import VideoPlayerCore from "@/components/video-player/VideoPlayerCore.vue";
import VideoInfo from "@/components/video-player/VideoInfo.vue";
import VideoActions from "@/components/video-player/VideoActions.vue";
import { getVideoDetail, incrementViewCount, getVideoList } from "@/api/video";
import { useUserStore } from "@/stores/user";
import type { Video, RecommendVideo } from "@/types/entity";

const route = useRoute();
const router = useRouter();
const userStore = useUserStore();

// 数据状态
const loading = ref(true);
const videoData = ref<Video | null>(null);
const isLiked = ref(false);
const isCollected = ref(false);
const showAuthDialog = ref(false);
const recommendVideos = ref<RecommendVideo[]>([]);

/**
 * 加载推荐视频
 */
const loadRecommendVideos = async () => {
  try {
    const response = await getVideoList({
      page: 1,
      page_size: 10,
      category_id: videoData.value?.category_id || null,
      keyword: undefined
    });

    if (response.success && response.data) {
      recommendVideos.value = response.data.items
        .filter((v) => v.id !== videoData.value?.id)
        .slice(0, 8)
        .map((v): RecommendVideo => ({
          id: v.id,
          title: v.title,
          cover: v.cover_url,
          uploader: v.uploader?.username || '未知',
          views: v.view_count || 0
        }));
    }
  } catch (error) {
    console.error('加载推荐视频失败:', error);
  }
};

// 获取封面URL，添加时间戳防止缓存
const getCoverUrl = (coverUrl: string | undefined): string => {
  if (!coverUrl) return '';
  // 添加时间戳防止缓存
  return `${coverUrl}?t=${Date.now()}`;
};

/**
 * 加载视频详情
 */
const loadVideoDetail = async () => {
  loading.value = true;

  try {
    const videoId = typeof route.params.id === 'string' ? parseInt(route.params.id, 10) : parseInt(route.params.id[0], 10);
    if (isNaN(videoId)) {
      ElMessage.error("无效的视频ID");
      router.push("/");
      return;
    }
    const response = await getVideoDetail(videoId);

    if (response.success) {
      videoData.value = response.data;

      // 加载推荐视频
      await loadRecommendVideos();

      // 如果视频还在转码中，则轮询等待转码完成
      if (videoData.value && (videoData.value.status === 0 || !videoData.value.video_url)) {
        await waitForTranscoding(videoId);
      }

      // 记录播放量
      await incrementViewCount(videoId);
    } else {
      ElMessage.error("视频不存在或已被删除");
      router.push("/");
    }
  } catch (error) {
    console.error("加载视频失败:", error);
    ElMessage.error("加载视频失败");
  } finally {
    loading.value = false;
  }
};

/**
 * 等待视频转码完成
 */
const waitForTranscoding = async (videoId: number) => {
  let attempts = 0;
  const maxAttempts = 120; // 最多等待 2 分钟
  const pollInterval = 1000; // 1 秒检查一次

  while (attempts < maxAttempts) {
    await new Promise((resolve) => setTimeout(resolve, pollInterval));
    attempts++;

    try {
      const response = await getVideoDetail(videoId);
      if (response.success && response.data.video_url) {
        videoData.value = response.data;
        ElMessage.success("视频转码完成，可以播放");
        return;
      }
    } catch (error) {
      console.warn(`轮询检查转码状态失败（第 ${attempts} 次）:`, error);
    }
  }

  ElMessage.warning("视频转码仍在进行中，请稍后刷新页面重试");
};

/**
 * 点赞
 */
const handleLike = async () => {
  if (!userStore.isLoggedIn) {
    ElMessage.warning("请先登录");
    return;
  }
  // TODO: 实现点赞逻辑
  ElMessage.info("点赞功能开发中");
};

const handleCollect = async () => {
  if (!userStore.isLoggedIn) {
    ElMessage.warning("请先登录");
    return;
  }
  // TODO: 实现收藏逻辑
  ElMessage.info("收藏功能开发中");
};

/**
 * 分享
 */
const handleShare = () => {
  ElMessage.info("分享功能开发中");
};

/**
 * 监听路由变化
 */
watch(
  () => route.params.id,
  (newId) => {
    if (newId) {
      loadVideoDetail();
    }
  }
);

onMounted(() => {
  loadVideoDetail();
});
</script>

<style lang="scss" scoped>
.video-player-page {
  min-height: 100vh;
  background: var(--bg-light);
}

.player-container {
  max-width: 1600px;
  margin: 0 auto;
  padding: var(--spacing-lg);
  display: grid;
  grid-template-columns: 1fr 360px;
  gap: var(--spacing-lg);
}

.main-content {
  min-width: 0;
}

.player-wrapper {
  background: #000;
  border-radius: var(--radius-lg);
  overflow: hidden;
  aspect-ratio: 16 / 9;
  margin-bottom: var(--spacing-lg);
}

.video-info-wrapper {
  background: var(--bg-white);
  border-radius: var(--radius-lg);
  padding: var(--spacing-xl);
}

.sidebar-content {
  position: sticky;
  top: 80px;
  height: fit-content;
  max-height: calc(100vh - 100px);
  overflow-y: auto;
}

.sidebar-title {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: var(--spacing-md);
  color: var(--text-primary);
}

.recommend-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.recommend-item {
  display: flex;
  gap: var(--spacing-sm);
  cursor: pointer;
  padding: var(--spacing-sm);
  border-radius: var(--radius-md);
  transition: background 0.2s;

  &:hover {
    background: var(--bg-light);
  }
}

.recommend-cover {
  width: 160px;
  height: 90px;
  object-fit: cover;
  border-radius: var(--radius-sm);
  flex-shrink: 0;
}

.recommend-info {
  flex: 1;
  min-width: 0;
}

.recommend-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: var(--spacing-xs);
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.recommend-meta {
  font-size: 12px;
  color: var(--text-secondary);
  display: flex;
  flex-direction: column;
  gap: 4px;
}

@media (max-width: 1200px) {
  .player-container {
    grid-template-columns: 1fr;
  }

  .sidebar-content {
    position: static;
    max-height: none;
  }

  .recommend-list {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  }
}

@media (max-width: 768px) {
  .player-container {
    padding: var(--spacing-md);
  }

  .video-info-wrapper {
    padding: var(--spacing-md);
  }

  .recommend-cover {
    width: 120px;
    height: 68px;
  }
}
</style>
