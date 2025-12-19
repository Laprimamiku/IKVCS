<template>
  <div class="video-info">
    <!-- 标题 -->
    <h1 class="video-title" :title="video.title">
      {{ video.title }}
    </h1>

    <!-- 基础元信息 -->
    <div class="video-meta">
      <span class="meta-item"> {{ formatNumber(video.view_count) }} 播放 </span>
      <span class="meta-item">
        {{ formatDate(video.created_at) }}
      </span>
      <span class="meta-item warning" v-if="video.status === 0"> 转码中 </span>
    </div>

    <!-- ✅ 互动区：中转 props & events -->
    <VideoActions
      :is-liked="isLiked"
      :is-collected="isCollected"
      :like-count="likeCount"
      :collect-count="collectCount"
      @like="$emit('like')"
      @collect="$emit('collect')"
      @share="$emit('share')"
      @report="$emit('report')"
    />

    <!-- 简介 -->
    <div class="video-desc" :class="{ collapsed: isDescCollapsed }">
      {{ video.description || "这个人很懒，什么都没有写~" }}
    </div>

    <div class="toggle-desc" @click="isDescCollapsed = !isDescCollapsed">
      {{ isDescCollapsed ? "展开更多" : "收起" }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import type { Video } from "@/shared/types/entity";
import { formatNumber, formatDate } from "@/shared/utils/formatters";
import VideoActions from "./VideoActions.vue";

/**
 * Props：全部来自 VideoPlayer
 * VideoInfo 不维护任何业务状态
 */
defineProps<{
  video: Video;
  isLiked: boolean;
  isCollected: boolean;
  likeCount: number;
  collectCount: number;
}>();

/**
 * Emits：原样向上抛
 */
defineEmits<{
  (e: "like"): void;
  (e: "collect"): void;
  (e: "share"): void;
  (e: "report"): void;
}>();

// 本组件只维护 UI 状态
const isDescCollapsed = ref(true);
</script>

<style lang="scss" scoped>
.video-info {
  margin-top: 16px;
  padding-bottom: 20px;
  border-bottom: 1px solid var(--border-light);

  .video-title {
    font-size: 20px;
    font-weight: 600;
    color: var(--text-primary);
    line-height: 28px;
    margin-bottom: 12px;
  }

  .video-meta {
    font-size: 13px;
    color: var(--text-tertiary);
    display: flex;
    align-items: center;
    gap: 16px;
    margin-bottom: 16px;

    .meta-item {
      &.warning {
        color: #FF9500;
        background: rgba(255, 149, 0, 0.1);
        padding: 2px 8px;
        border-radius: var(--radius-sm);
        font-size: 12px;
      }
    }
  }

  .video-desc {
    font-size: 14px;
    color: var(--text-secondary);
    line-height: 22px;
    white-space: pre-wrap;
    margin-top: 12px;

    &.collapsed {
      display: -webkit-box;
      -webkit-box-orient: vertical;
      -webkit-line-clamp: 2;
      line-clamp: 2;
      overflow: hidden;
    }
  }

  .toggle-desc {
    font-size: 13px;
    color: var(--text-tertiary);
    margin-top: 8px;
    cursor: pointer;
    transition: color 0.2s;
    display: inline-block;

    &:hover {
      color: var(--primary-color);
    }
  }
}
</style>
