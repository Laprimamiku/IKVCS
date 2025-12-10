<template>
  <div class="video-info-section">
    <!-- 视频标题和统计 -->
    <div class="video-header">
      <h1 class="video-title">{{ videoData?.title || '加载中...' }}</h1>
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
        <p>{{ videoData?.description || '暂无简介' }}</p>
      </div>
      <el-button
        v-if="videoData?.description && videoData.description.length > 100"
        text
        @click="descExpanded = !descExpanded"
      >
        {{ descExpanded ? '收起' : '展开' }}
        <el-icon>
          <component :is="descExpanded ? ArrowUp : ArrowDown" />
        </el-icon>
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { View, Calendar, CircleCheck, ArrowUp, ArrowDown } from '@element-plus/icons-vue'
import type { Video } from '@/types/entity'
import { formatNumber } from '@/utils/formatters'

defineProps<{
  videoData: Video | null
}>()

const descExpanded = ref(false)

const formatDate = (dateStr?: string): string => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })
}
</script>

<style lang="scss" scoped>
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

.uploader-section {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-lg) 0;
  border-top: 1px solid var(--border-light);
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

@media (max-width: 768px) {
  .video-info-section {
    padding: var(--spacing-md);
  }

  .video-title {
    font-size: var(--font-size-xl);
  }

  .uploader-section {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--spacing-md);
  }
}
</style>

