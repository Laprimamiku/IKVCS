<template>
  <div class="video-actions-bar">
    <div
      class="action-item"
      :class="{ active: isLiked }"
      @click="$emit('like')"
    >
      <el-icon :size="22" class="like-icon" :class="{ 'is-liked': isLiked }">
        <CircleCheckFilled />
      </el-icon>
      <span>{{ formatNumber(likeCount) || "点赞" }}</span>
    </div>

    <div
      class="action-item"
      :class="{ active: isCollected }"
      @click="$emit('collect')"
    >
      <el-icon :size="22">
        <StarFilled v-if="isCollected" />
        <Star v-else />
      </el-icon>
      <span>{{ formatNumber(collectCount) || "收藏" }}</span>
    </div>

    <div class="action-item" @click="$emit('share')">
      <el-icon :size="22"><Share /></el-icon>
      <span>分享</span>
    </div>

    <div class="action-item report-btn" @click="$emit('report')">
      <el-icon :size="22"><Warning /></el-icon>
      <span>举报</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import {
  Star,
  StarFilled,
  Share,
  CircleCheckFilled,
  Warning,
} from "@element-plus/icons-vue";
import { formatNumber } from "@/features/video/player/utils/videoFormatters";

defineProps<{
  isLiked: boolean;
  isCollected: boolean;
  likeCount?: number;
  collectCount?: number;
}>();

defineEmits<{
  like: [];
  collect: [];
  share: [];
  report: [];
}>();
</script>

<style lang="scss" scoped>
.video-actions-bar {
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 16px 0;
  border-top: 1px solid var(--border-light);
  border-bottom: 1px solid var(--border-light);
  margin: 16px 0;

  .action-item {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 14px;
    color: var(--text-secondary);
    cursor: pointer;
    transition: all 0.2s;
    user-select: none;
    padding: 6px 12px;
    border-radius: var(--radius-md);

    &:hover {
      color: var(--primary-color);
      background: var(--primary-light);
    }

    &.active {
      color: var(--primary-color);
      background: var(--primary-light);
      
      .el-icon {
        color: var(--primary-color);
      }
      
      .like-icon {
        transform: rotate(-15deg) scale(1.1);
      }
    }
    
    .like-icon {
      transition: transform 0.2s;
      &.is-liked {
        color: var(--bili-pink);
        transform: rotate(-15deg) scale(1.1);
      }
    }

    .el-icon {
      transition: color 0.2s;
    }

    &.report-btn {
      margin-left: auto;
      color: var(--text-tertiary);
      
      &:hover {
        color: #F56C6C;
        background: rgba(245, 108, 108, 0.1);
      }
    }
  }
}
</style>
