<template>
  <div class="video-player-page">
    <!-- 视频播放器区域 -->
    <div class="player-container">
      <div class="player-wrapper">
        <!-- HLS 视频播放器 -->
        <video
          ref="videoRef"
          class="video-js vjs-big-play-centered"
          controls
          preload="auto"
        >
          <track
            v-if="videoData?.subtitle_url"
            kind="subtitles"
            :src="videoData.subtitle_url"
            srclang="zh"
            label="中文"
            default
          />
        </video>
      </div>
    </div>

    <!-- 视频信息区域 -->
    <div class="content-container">
      <div class="video-info-section">
        <!-- 视频标题和统计 -->
        <div class="video-header">
          <h1 class="video-title">{{ videoData?.title || "加载中..." }}</h1>
          <div class="video-stats">
            <span class="stat-item">
              <el-icon><View /></el-icon>
              {{ formatNumber(videoData?.view_count || 0) }} 播放
            </span>
            <span class="stat-item">
              <el-icon><Calendar /></el-icon>
              {{ formatDate(videoData?.created_at) }}
            </span>
          </div>
        </div>

        <!-- 操作按钮区 -->
        <div class="action-bar">
          <el-button
            :type="isLiked ? 'primary' : 'default'"
            :icon="isLiked ? StarFilled : Star"
            @click="handleLike"
          >
            {{ isLiked ? "已点赞" : "点赞" }}
            <span v-if="videoData?.like_count"
              >({{ formatNumber(videoData.like_count) }})</span
            >
          </el-button>

          <el-button
            :type="isCollected ? 'primary' : 'default'"
            :icon="isCollected ? FolderChecked : Folder"
            @click="handleCollect"
          >
            {{ isCollected ? "已收藏" : "收藏" }}
            <span v-if="videoData?.collect_count"
              >({{ formatNumber(videoData.collect_count) }})</span
            >
          </el-button>

          <el-button :icon="Share">分享</el-button>
        </div>

        <!-- UP主信息 -->
        <div class="uploader-section">
          <div class="uploader-info">
            <el-avatar
              :src="videoData?.uploader?.avatar"
              :size="48"
              class="uploader-avatar"
            />
            <div class="uploader-details">
              <div class="uploader-name">
                {{
                  videoData?.uploader?.nickname || videoData?.uploader?.username
                }}
                <el-icon
                  v-if="videoData?.uploader?.role === 'admin'"
                  class="verified-icon"
                >
                  <CircleCheck />
                </el-icon>
              </div>
              <div class="uploader-meta">
                上传于 {{ formatDate(videoData?.created_at) }}
              </div>
            </div>
          </div>
          <el-button type="primary" size="large">关注</el-button>
        </div>

        <!-- 视频描述 -->
        <div class="video-description">
          <div class="description-header">
            <h3>视频简介</h3>
          </div>
          <div
            class="description-content"
            :class="{ 'is-expanded': descExpanded }"
          >
            <p>{{ videoData?.description || "暂无简介" }}</p>
          </div>
          <el-button
            v-if="videoData?.description && videoData.description.length > 100"
            text
            @click="descExpanded = !descExpanded"
          >
            {{ descExpanded ? "收起" : "展开" }}
            <el-icon>
              <component :is="descExpanded ? ArrowUp : ArrowDown" />
            </el-icon>
          </el-button>
        </div>
      </div>
    </div>

    <!-- 加载状态 -->
    <el-skeleton v-if="loading" animated class="content-container">
      <template #template>
        <el-skeleton-item variant="h1" style="width: 60%" />
        <el-skeleton-item variant="text" style="width: 40%; margin-top: 16px" />
        <el-skeleton-item
          variant="rect"
          style="height: 100px; margin-top: 24px"
        />
      </template>
    </el-skeleton>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import {
  View,
  Calendar,
  Star,
  StarFilled,
  Folder,
  FolderChecked,
  Share,
  CircleCheck,
  ArrowUp,
  ArrowDown,
} from "@element-plus/icons-vue";
import Hls from "hls.js";
import { getVideoDetail, incrementViewCount } from "@/api/video";
import { useUserStore } from "@/stores/user";

const route = useRoute();
const router = useRouter();
const userStore = useUserStore();

// 静态资源基址（用于拼接 m3u8、字幕等相对路径）
const resolveFileUrl = (path) => {
  if (!path) return "";
  if (path.startsWith("http")) return path;
  const base =
    import.meta.env.VITE_FILE_BASE_URL ||
    (import.meta.env.VITE_API_BASE_URL
      ? import.meta.env.VITE_API_BASE_URL.replace(/\/api\/v1$/, "")
      : window.location.origin);
  return `${base}${path}`;
};

// 视频播放器
const videoRef = ref(null);
let hls = null;

// 数据状态
const loading = ref(true);
const videoData = ref(null);
const isLiked = ref(false);
const isCollected = ref(false);
const descExpanded = ref(false);

/**
 * 格式化数字
 */
const formatNumber = (num) => {
  if (!num) return "0";
  if (num >= 100000000) {
    return (num / 100000000).toFixed(1) + "亿";
  }
  if (num >= 10000) {
    return (num / 10000).toFixed(1) + "万";
  }
  return num.toString();
};

/**
 * 格式化日期
 */
const formatDate = (dateStr) => {
  if (!dateStr) return "";
  const date = new Date(dateStr);
  return date.toLocaleDateString("zh-CN", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
};

/**
 * 初始化 HLS 播放器
 */
const initPlayer = () => {
  if (!videoData.value?.video_url) return;

  const videoElement = videoRef.value;
  const videoUrl = videoData.value.video_url;

  // 检查是否是 HLS 格式
  if (videoUrl.endsWith(".m3u8")) {
    if (Hls.isSupported()) {
      hls = new Hls({
        enableWorker: true,
        lowLatencyMode: true,
      });

      hls.loadSource(videoUrl);
      hls.attachMedia(videoElement);

      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        console.log("HLS manifest loaded");
      });

      hls.on(Hls.Events.ERROR, (event, data) => {
        console.error("HLS error:", data);
        if (data.fatal) {
          switch (data.type) {
            case Hls.ErrorTypes.NETWORK_ERROR:
              ElMessage.error("网络错误，无法加载视频");
              hls.startLoad();
              break;
            case Hls.ErrorTypes.MEDIA_ERROR:
              ElMessage.error("媒体错误");
              hls.recoverMediaError();
              break;
            default:
              ElMessage.error("播放器错误");
              break;
          }
        }
      });
    } else if (videoElement.canPlayType("application/vnd.apple.mpegurl")) {
      // Safari 原生支持 HLS
      videoElement.src = videoUrl;
    } else {
      ElMessage.error("您的浏览器不支持 HLS 播放");
    }
  } else {
    // 普通视频格式
    videoElement.src = videoUrl;
  }
};

/**
 * 加载视频详情
 */
const loadVideoDetail = async () => {
  loading.value = true;

  try {
    const videoId = route.params.id;
    const response = await getVideoDetail(videoId);

    if (response.success) {
      const detail = {
        ...response.data,
        video_url: resolveFileUrl(response.data.video_url),
        subtitle_url: resolveFileUrl(response.data.subtitle_url),
      };
      videoData.value = detail;

      // 如果视频还在转码中（status=0），则轮询等待转码完成
      if (detail.status === 0 || !detail.video_url) {
        await waitForTranscoding(videoId);
      }

      // 初始化播放器
      setTimeout(() => {
        initPlayer();
      }, 100);

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
 * 轮询检查视频状态，直到转码完成
 */
const waitForTranscoding = async (videoId) => {
  let attempts = 0;
  const maxAttempts = 120; // 最多等待 2 分钟（每次间隔 1 秒）
  const pollInterval = 1000; // 1 秒检查一次

  while (attempts < maxAttempts) {
    await new Promise((resolve) => setTimeout(resolve, pollInterval));
    attempts++;

    try {
      const response = await getVideoDetail(videoId);
      if (response.success && response.data.video_url) {
        const detail = {
          ...response.data,
          video_url: resolveFileUrl(response.data.video_url),
          subtitle_url: resolveFileUrl(response.data.subtitle_url),
        };
        videoData.value = detail;
        ElMessage.success("视频转码完成，可以播放");
        return;
      }
    } catch (error) {
      // 继续轮询
      console.warn(`轮询检查转码状态失败（第 ${attempts} 次）:`, error);
    }
  }

  // 等待超时
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

  try {
    if (isLiked.value) {
      // TODO: 调用取消点赞 API
      ElMessage.success("已取消点赞");
      isLiked.value = false;
      if (videoData.value) {
        videoData.value.like_count = Math.max(
          0,
          (videoData.value.like_count || 0) - 1
        );
      }
    } else {
      // TODO: 调用点赞 API
      ElMessage.success("点赞成功");
      isLiked.value = true;
      if (videoData.value) {
        videoData.value.like_count = (videoData.value.like_count || 0) + 1;
      }
    }
  } catch (error) {
    console.error("点赞操作失败:", error);
    ElMessage.error("操作失败");
  }
};

/**
 * 收藏
 */
const handleCollect = async () => {
  if (!userStore.isLoggedIn) {
    ElMessage.warning("请先登录");
    return;
  }

  try {
    if (isCollected.value) {
      // TODO: 调用取消收藏 API
      ElMessage.success("已取消收藏");
      isCollected.value = false;
      if (videoData.value) {
        videoData.value.collect_count = Math.max(
          0,
          (videoData.value.collect_count || 0) - 1
        );
      }
    } else {
      // TODO: 调用收藏 API
      ElMessage.success("收藏成功");
      isCollected.value = true;
      if (videoData.value) {
        videoData.value.collect_count =
          (videoData.value.collect_count || 0) + 1;
      }
    }
  } catch (error) {
    console.error("收藏操作失败:", error);
    ElMessage.error("操作失败");
  }
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

onUnmounted(() => {
  // 清理 HLS 实例
  if (hls) {
    hls.destroy();
    hls = null;
  }
});
</script>

<style scoped>
.video-player-page {
  min-height: 100vh;
  background: var(--bg-light);
}

/* ==================== 播放器容器 ==================== */
.player-container {
  background: #000;
  position: relative;
}

.player-wrapper {
  max-width: 1400px;
  margin: 0 auto;
  position: relative;
  padding-top: 56.25%; /* 16:9 宽高比 */
}

.player-wrapper video {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
}

/* Video.js 样式覆盖 */
.video-js {
  width: 100%;
  height: 100%;
}

.video-js .vjs-big-play-button {
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  border-radius: 50%;
  width: 80px;
  height: 80px;
  font-size: 48px;
  border: none;
  background: rgba(255, 255, 255, 0.9);
}

.video-js .vjs-big-play-button:hover {
  background: rgba(255, 255, 255, 1);
}

/* ==================== 内容容器 ==================== */
.content-container {
  max-width: 1400px;
  margin: 0 auto;
  padding: var(--spacing-lg);
}

/* ==================== 视频信息区 ==================== */
.video-info-section {
  background: var(--bg-white);
  border-radius: var(--radius-lg);
  padding: var(--spacing-xl);
  margin-bottom: var(--spacing-lg);
}

.video-header {
  margin-bottom: var(--spacing-lg);
}

.video-title {
  font-size: var(--font-size-2xl);
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 var(--spacing-md) 0;
  line-height: 1.4;
}

.video-stats {
  display: flex;
  gap: var(--spacing-lg);
  color: var(--text-secondary);
  font-size: var(--font-size-sm);
}

.stat-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
}

/* ==================== 操作按钮区 ==================== */
.action-bar {
  display: flex;
  gap: var(--spacing-md);
  padding: var(--spacing-lg) 0;
  border-top: 1px solid var(--border-light);
  border-bottom: 1px solid var(--border-light);
}

/* ==================== UP主信息 ==================== */
.uploader-section {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-lg) 0;
  border-bottom: 1px solid var(--border-light);
}

.uploader-info {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.uploader-avatar {
  flex-shrink: 0;
}

.uploader-details {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.uploader-name {
  font-size: var(--font-size-lg);
  font-weight: 500;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
}

.verified-icon {
  color: var(--primary-color);
  font-size: 18px;
}

.uploader-meta {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}

/* ==================== 视频描述 ==================== */
.video-description {
  padding-top: var(--spacing-lg);
}

.description-header h3 {
  font-size: var(--font-size-lg);
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 var(--spacing-md) 0;
}

.description-content {
  color: var(--text-regular);
  line-height: 1.8;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 100px;
  overflow: hidden;
  transition: max-height var(--transition-base);
}

.description-content.is-expanded {
  max-height: none;
}

.description-content p {
  margin: 0;
}

/* ==================== 响应式设计 ==================== */
@media (max-width: 768px) {
  .content-container {
    padding: var(--spacing-md);
  }

  .video-info-section {
    padding: var(--spacing-md);
  }

  .video-title {
    font-size: var(--font-size-xl);
  }

  .action-bar {
    flex-wrap: wrap;
  }

  .uploader-section {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--spacing-md);
  }
}
</style>
