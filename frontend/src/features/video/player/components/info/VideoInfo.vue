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
}>();

// 本组件只维护 UI 状态
const isDescCollapsed = ref(true);
</script>

<style lang="scss" scoped>
.video-info {
  margin-top: 16px;
  padding-bottom: 20px;
  border-bottom: 1px solid #e3e5e7;

  .video-title {
    font-size: 20px;
    font-weight: 500;
    color: #18191c;
    line-height: 28px;
    margin-bottom: 8px;
  }

  .video-meta {
    font-size: 13px;
    color: #9499a0;
    display: flex;
    align-items: center;
    gap: 16px;
    margin-bottom: 16px;

    .meta-item {
      &.warning {
        color: #e6a23c;
      }
    }
  }

  .video-desc {
    font-size: 13px;
    color: #18191c;
    line-height: 20px;
    white-space: pre-wrap;
    margin-top: 12px;

    &.collapsed {
      display: -webkit-box;
      -webkit-box-orient: vertical;
      -webkit-line-clamp: 2;
      /* ✅ 新增标准属性以消除警告 */
      line-clamp: 2;
      overflow: hidden;
    }
  }

  .toggle-desc {
    font-size: 12px;
    color: #9499a0;
    margin-top: 8px;
    cursor: pointer;

    &:hover {
      color: #00aeec;
    }
  }
}
</style>
