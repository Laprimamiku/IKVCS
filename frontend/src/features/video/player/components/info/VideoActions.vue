<template>
  <div class="video-actions-bar">
    <div
      class="action-item"
      :class="{ active: isLiked }"
      @click="$emit('like')"
    >
      <el-icon :size="22">
        <component :is="isLiked ? CircleCheckFilled : GoodTwo" />
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
  </div>
</template>

<script setup lang="ts">
import {
  Star,
  StarFilled,
  Share,
  CircleCheckFilled,
} from "@element-plus/icons-vue";
import { Warning as GoodTwo } from "@element-plus/icons-vue";
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
}>();
</script>

<style lang="scss" scoped>
.video-actions-bar {
  display: flex;
  align-items: center;
  gap: 32px;
  padding: 12px 0;
  border-top: 1px solid #e3e5e7;
  border-bottom: 1px solid #e3e5e7;
  margin-bottom: 16px;

  .action-item {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 15px;
    color: #61666d;
    cursor: pointer;
    transition: color 0.2s;
    user-select: none;

    &:hover {
      color: #00aeec;
    }

    &.active {
      color: #00aeec;
    }
  }
}
</style>
