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
  padding: 24px 0; // 增加内边距
}

.progress-info {
  margin-bottom: 32px; // 增加间距

  h3 {
    font-size: 22px;
    color: var(--text-primary);
    margin-bottom: 12px;
    font-weight: 600;
  }
}

.progress-detail {
  font-size: 15px;
  color: var(--text-secondary);
  line-height: 1.6;
}

.progress-bar-wrapper {
  margin: 40px 0; // 增加间距
  padding: 0 20px;
}

.progress-details {
  display: flex;
  justify-content: space-around;
  margin: 32px 0; // 增加间距
  padding: 24px; // 增加内边距
  background: #f8f9fa;
  border-radius: 8px;
  gap: 24px; // 增加项之间的间距
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
  gap: 16px; // 增加按钮间距
  margin-top: 40px; // 增加上边距
  padding-top: 24px;
  border-top: 1px solid #e5e7eb; // 添加分隔线
}

@media (max-width: 768px) {
  .progress-details {
    flex-direction: column;
    gap: var(--spacing-md);
  }
}
</style>

