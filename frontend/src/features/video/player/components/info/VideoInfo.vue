<template>
  <div class="video-info-card">
    <h1 class="video-title" :title="video?.title">
      {{ video?.title }}
    </h1>

    <div class="video-meta-data">
      <span class="meta-item">
        <el-icon><VideoPlay /></el-icon>
        {{ formatNumber(video?.view_count) }}
      </span>
      <span class="meta-item">
        <el-icon><ChatLineSquare /></el-icon>
        {{ danmakuCount }}
      </span>
      <span class="meta-item">
        {{ formatDate(video?.created_at) }}
      </span>
      <span class="meta-item warning" v-if="video?.status === 0">
        <el-icon><Loading /></el-icon>
        转码中
      </span>
    </div>

    <slot name="actions" />

    <div class="video-desc">
      {{ video?.description || "这个人很懒，什么都没有写~" }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { VideoPlay, ChatLineSquare, Loading } from "@element-plus/icons-vue";
import type { Video } from "@/shared/types/entity";
import { formatNumber, formatDate } from "@/features/video/player/utils/videoFormatters";

defineProps<{
  video: Video | null;
  danmakuCount: number;
}>();
</script>

<style lang="scss" scoped>
.video-info-card {
  margin-top: 24px;
  padding-bottom: 20px;
  border-bottom: 1px solid #e3e5e7;

  .video-title {
    font-size: 20px;
    font-weight: 500;
    color: #18191c;
    line-height: 28px;
    margin-bottom: 8px;
  }

  .video-meta-data {
    font-size: 13px;
    color: #9499a0;
    display: flex;
    align-items: center;
    gap: 16px;
    margin-bottom: 16px;

    .meta-item {
      display: flex;
      align-items: center;
      gap: 4px;

      &.warning {
        color: #e6a23c;
      }
    }
  }

  .video-desc {
    font-size: 14px;
    color: #18191c;
    line-height: 24px;
    white-space: pre-wrap;
    overflow: hidden;
  }
}
</style>
