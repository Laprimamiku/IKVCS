<template>
  <div class="upload-progress">
    <div class="progress-info">
      <h3>{{ status }}</h3>
      <p class="progress-detail">{{ detail }}</p>
    </div>

    <!-- 总体进度 -->
    <div class="progress-bar-wrapper">
      <el-progress
        :percentage="progress"
        :status="complete ? 'success' : undefined"
        :stroke-width="20"
      />
    </div>

    <!-- 详细进度信息 -->
    <div class="progress-details">
      <div class="detail-item">
        <span class="label">已上传分片：</span>
        <span class="value">{{ uploadedChunks }} / {{ totalChunks }}</span>
      </div>
      <div class="detail-item">
        <span class="label">上传速度：</span>
        <span class="value">{{ speed }}</span>
      </div>
      <div class="detail-item">
        <span class="label">剩余时间：</span>
        <span class="value">{{ remainingTime }}</span>
      </div>
    </div>

    <!-- 操作按钮 -->
    <div class="progress-actions">
      <el-button
        v-if="!complete && !uploading"
        type="primary"
        size="large"
        @click="$emit('resume')"
      >
        继续上传
      </el-button>
      <el-button
        v-if="uploading"
        type="warning"
        size="large"
        @click="$emit('pause')"
      >
        暂停上传
      </el-button>
      <el-button
        v-if="complete"
        type="success"
        size="large"
        @click="$emit('go-home')"
      >
        返回首页
      </el-button>
      <el-button
        v-if="complete"
        size="large"
        @click="$emit('upload-another')"
      >
        继续上传
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  status: string
  detail: string
  progress: number
  complete: boolean
  uploading: boolean
  uploadedChunks: number
  totalChunks: number
  speed: string
  remainingTime: string
}>()

defineEmits<{
  resume: []
  pause: []
  'go-home': []
  'upload-another': []
}>()
</script>

<style lang="scss" scoped>
.upload-progress {
  text-align: center;
}

.progress-info {
  margin-bottom: var(--spacing-xl);

  h3 {
    font-size: var(--font-size-xl);
    color: var(--text-primary);
    margin-bottom: var(--spacing-sm);
  }
}

.progress-detail {
  font-size: var(--font-size-base);
  color: var(--text-secondary);
}

.progress-bar-wrapper {
  margin: var(--spacing-2xl) 0;
}

.progress-details {
  display: flex;
  justify-content: space-around;
  margin: var(--spacing-xl) 0;
  padding: var(--spacing-lg);
  background: var(--bg-light);
  border-radius: var(--radius-md);
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.detail-item .label {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}

.detail-item .value {
  font-size: var(--font-size-lg);
  font-weight: 600;
  color: var(--text-primary);
}

.progress-actions {
  display: flex;
  justify-content: center;
  gap: var(--spacing-md);
  margin-top: var(--spacing-2xl);
}

@media (max-width: 768px) {
  .progress-details {
    flex-direction: column;
    gap: var(--spacing-md);
  }
}
</style>

