<template>
  <div class="video-item">
    <!-- 视频封面 -->
    <div class="video-cover" @click="$emit('view', video.id)">
      <img v-if="video.cover_url" :src="getCoverUrl(video.cover_url)" alt="封面" />
      <div v-else class="cover-placeholder">
        <el-icon :size="48"><VideoPlay /></el-icon>
      </div>
      <div class="status-badge" :class="getStatusClass(video.status)">
        {{ getStatusText(video.status) }}
      </div>
      <div class="video-duration" v-if="video.duration">
        {{ formatDuration(video.duration) }}
      </div>
    </div>

    <!-- 视频信息 -->
    <div class="video-info">
      <h3 class="video-title" :title="video.title">{{ video.title }}</h3>
      <div class="video-meta">
        <span class="meta-item">
          <el-icon><View /></el-icon>
          {{ formatNumber(video.view_count) }}
        </span>
        <span class="meta-item">
          <el-icon><Star /></el-icon>
          {{ formatNumber(video.like_count) }}
        </span>
        <span class="meta-item">
          <el-icon><Collection /></el-icon>
          {{ formatNumber(video.collect_count) }}
        </span>
      </div>
      <div class="video-actions">
        <el-button size="small" @click.stop="$emit('view', video.id)">
          <el-icon><View /></el-icon>
          查看
        </el-button>
        <el-button size="small" type="primary" @click.stop="$emit('edit', video)">
          <el-icon><Edit /></el-icon>
          编辑
        </el-button>
        <el-button size="small" type="danger" @click.stop="$emit('delete', video)">
          <el-icon><Delete /></el-icon>
          删除
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { View, Star, Collection, VideoPlay, Edit, Delete } from '@element-plus/icons-vue'
import type { Video } from "@/shared/types/entity"
import { formatDuration, formatNumber } from "@/shared/utils/formatters"


defineProps<{
  video: Video
}>()

defineEmits<{
  view: [id: number]
  edit: [video: Video]
  delete: [video: Video]
}>()

const getStatusText = (status?: number): string => {
  const map: Record<number, string> = {
    0: '转码中',
    1: '审核中',
    2: '已发布',
    3: '已拒绝'
  }
  return map[status ?? -1] || '未知'
}

const getStatusClass = (status?: number): string => {
  const map: Record<number, string> = {
    0: 'status-transcoding',
    1: 'status-reviewing',
    2: 'status-published',
    3: 'status-rejected'
  }
  return map[status ?? -1] || ''
}

// 获取封面URL，添加时间戳防止缓存（API层已处理URL，这里只需添加时间戳）
const getCoverUrl = (coverUrl: string | undefined): string => {
  if (!coverUrl) return ''
  // 添加时间戳防止缓存
  return `${coverUrl}?t=${Date.now()}`
}
</script>

<style lang="scss" scoped>
.video-item {
  background: var(--bg-white);
  border-radius: var(--radius-md);
  overflow: hidden;
  transition: all var(--transition-base);
  cursor: pointer;
}

.video-item:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-hover);
}

.video-cover {
  position: relative;
  width: 100%;
  padding-top: 56.25%; /* 16:9 */
  overflow: hidden;
  background: var(--bg-light);
}

.video-cover img {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.cover-placeholder {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-placeholder);
  background: var(--bg-light);
}

.status-badge {
  position: absolute;
  top: 8px;
  left: 8px;
  padding: 4px 10px;
  border-radius: var(--radius-sm);
  font-size: var(--font-size-xs);
  font-weight: 500;
  color: white;
  backdrop-filter: blur(4px);
}

.status-transcoding {
  background: rgba(64, 158, 255, 0.9);
}

.status-reviewing {
  background: rgba(230, 162, 60, 0.9);
}

.status-published {
  background: rgba(103, 194, 58, 0.9);
}

.status-rejected {
  background: rgba(245, 108, 108, 0.9);
}

.video-duration {
  position: absolute;
  bottom: 8px;
  right: 8px;
  padding: 2px 6px;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(4px);
  color: white;
  font-size: var(--font-size-xs);
  border-radius: var(--radius-sm);
}

.video-info {
  padding: var(--spacing-md);
}

.video-title {
  margin: 0 0 var(--spacing-sm) 0;
  font-size: var(--font-size-base);
  font-weight: 500;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.video-meta {
  display: flex;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-sm);
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.video-actions {
  display: flex;
  gap: var(--spacing-sm);
}

@media (max-width: 768px) {
  .video-actions {
    flex-wrap: wrap;
  }
}
</style>

