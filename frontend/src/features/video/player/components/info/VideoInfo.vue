<template>
  <div class="video-info-container">
    <h1 class="video-title" :title="video.title">
      {{ video.title }}
    </h1>

    <div class="video-data-row">
      <span class="view-data" title="播放量">
        <el-icon><VideoPlay /></el-icon>&nbsp;{{
          formatNumber(video.view_count)
        }}
      </span>
      <span class="danmaku-data" title="弹幕数">
        <el-icon><ChatDotRound /></el-icon>&nbsp;{{
          formatNumber(danmakuCount)
        }}
      </span>
      <span class="upload-time">
        {{ formatDateTime(video.created_at) }}
      </span>
      <span v-if="video.status === 0" class="status-tag warning">
        <el-icon><Warning /></el-icon> 转码中
      </span>
    </div>

    <div class="divider"></div>

    <div class="toolbar-container">
      <div class="toolbar-left">
        <div
          class="tool-item"
          :class="{ active: isLiked }"
          @click="$emit('like')"
        >
          <el-icon v-if="isLiked"><Select /></el-icon>
          <el-icon v-else><Pointer /></el-icon>
          <span class="text">{{
            likeCount > 0 ? formatNumber(likeCount) : "点赞"
          }}</span>
        </div>

        <div class="tool-item" @click="handleCoin">
          <el-icon><Coin /></el-icon>
          <span class="text">投币</span>
        </div>

        <div
          class="tool-item"
          :class="{ active: isCollected }"
          @click="$emit('collect')"
        >
          <el-icon><Star /></el-icon>
          <span class="text">{{
            collectCount > 0 ? formatNumber(collectCount) : "收藏"
          }}</span>
        </div>

        <div class="tool-item" @click="$emit('share')">
          <el-icon><Share /></el-icon>
          <span class="text">分享</span>
        </div>
      </div>

      <div class="toolbar-right">
        <div class="tool-item text-only" @click="$emit('report')">
          <span class="text">举报</span>
        </div>
      </div>
    </div>

    <div class="desc-container">
      <div class="desc-text" :class="{ 'is-collapsed': isDescCollapsed }">
        {{ video.description || "-" }}
      </div>
      <div class="toggle-btn" @click="isDescCollapsed = !isDescCollapsed">
        {{ isDescCollapsed ? "展开更多" : "收起" }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { ElMessage } from "element-plus";
import type { Video } from "@/shared/types/entity";
import { formatNumber } from "@/shared/utils/formatters";
import {
  VideoPlay,
  ChatDotRound,
  Warning,
  Pointer,
  Star,
  Share,
  Coin,
  Select,
} from "@element-plus/icons-vue";

defineProps<{
  video: Video;
  danmakuCount: number;
  isLiked: boolean;
  isCollected: boolean;
  likeCount: number;
  collectCount: number;
}>();

const emit = defineEmits<{
  (e: "like"): void;
  (e: "collect"): void;
  (e: "share"): void;
  (e: "report"): void;
}>();

const isDescCollapsed = ref(true);

const formatDateTime = (str: string) => {
  return new Date(str)
    .toLocaleString("zh-CN", { hour12: false })
    .replace(/\//g, "-");
};

const handleCoin = () => {
  ElMessage.success("投币成功！(模拟)");
};
</script>

<style lang="scss" scoped>
.video-info-container {
  padding-top: 20px;
  padding-bottom: 24px;
  border-bottom: 1px solid var(--border-color);

  .video-title {
    font-size: 20px;
    font-weight: 600;
    color: var(--text-primary);
    line-height: 28px;
    margin-bottom: 10px;
    overflow: hidden;
    text-overflow: ellipsis;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    line-clamp: 2;
    -webkit-box-orient: vertical;
  }

  .video-data-row {
    display: flex;
    align-items: center;
    color: var(--text-tertiary);
    font-size: 13px;
    gap: 20px;

    .el-icon {
      font-size: 16px;
      margin-right: 4px;
      vertical-align: text-bottom;
    }

    .status-tag.warning {
      color: var(--warning-color);
      background: #fff0e6;
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 12px;
    }
  }

  .divider {
    height: 1px;
    background: var(--divider-color);
    margin: 16px 0;
  }

  /* 互动工具栏 */
  .toolbar-container {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;

    .toolbar-left {
      display: flex;
      gap: 32px; /* 间距拉大 */
    }

    .tool-item {
      display: flex;
      align-items: center;
      gap: 6px;
      cursor: pointer;
      color: var(--text-secondary);
      font-size: 14px;
      transition: all 0.2s;

      .el-icon {
        font-size: 24px;
      } /* 图标做大 */

      &:hover {
        color: var(--primary-color);
      }

      &.active {
        color: var(--primary-color);
      }

      &.text-only {
        font-size: 12px;
        color: var(--text-tertiary);
        &:hover {
          color: var(--text-secondary);
        }
      }
    }
  }

  .desc-container {
    font-size: 14px;
    line-height: 24px;

    .desc-text {
      white-space: pre-wrap;
      color: var(--text-primary);
      &.is-collapsed {
        height: 72px; /* 3行高度 */
        overflow: hidden;
        display: -webkit-box;
        -webkit-line-clamp: 3;
        line-clamp: 3;
        -webkit-box-orient: vertical;
      }
    }

    .toggle-btn {
      margin-top: 10px;
      font-size: 13px;
      color: var(--text-tertiary);
      cursor: pointer;
      &:hover {
        color: var(--primary-color);
      }
    }
  }
}
</style>
