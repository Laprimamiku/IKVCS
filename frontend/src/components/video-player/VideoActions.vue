<template>
  <div class="action-bar">
    <el-button
      :type="isLiked ? 'primary' : 'default'"
      :icon="isLiked ? StarFilled : Star"
      @click="$emit('like')"
    >
      {{ isLiked ? '已点赞' : '点赞' }}
      <span v-if="videoData?.like_count"
        >({{ formatNumber(videoData.like_count) }})</span
      >
    </el-button>

    <el-button
      :type="isCollected ? 'primary' : 'default'"
      :icon="isCollected ? FolderChecked : Folder"
      @click="$emit('collect')"
    >
      {{ isCollected ? '已收藏' : '收藏' }}
      <span v-if="videoData?.collect_count"
        >({{ formatNumber(videoData.collect_count) }})</span
      >
    </el-button>

    <el-button :icon="Share" @click="$emit('share')">分享</el-button>
  </div>
</template>

<script setup lang="ts">
import { Star, StarFilled, Folder, FolderChecked, Share } from '@element-plus/icons-vue'
import type { VideoDetailResponse } from '@/types/entity'
import { formatNumber } from '@/utils/formatters'

defineProps<{
  videoData: VideoDetailResponse | null
  isLiked: boolean
  isCollected: boolean
}>()

defineEmits<{
  like: []
  collect: []
  share: []
}>()
</script>

<style lang="scss" scoped>
.action-bar {
  display: flex;
  gap: var(--spacing-md);
  padding: var(--spacing-lg) 0;
  border-top: 1px solid var(--border-light);
  border-bottom: 1px solid var(--border-light);
}

@media (max-width: 768px) {
  .action-bar {
    flex-wrap: wrap;
  }
}
</style>

