<template>
  <div class="header-section">
    <h1 class="page-title">我的视频</h1>
    <el-button type="primary" @click="$emit('upload')">
      <el-icon><Upload /></el-icon>
      上传视频
    </el-button>
  </div>
</template>

<script setup lang="ts">
import { Upload } from '@element-plus/icons-vue'

defineEmits<{
  upload: []
}>()
</script>

<style lang="scss" scoped>
.header-section {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-lg);
  background: var(--bg-white);
  padding: var(--spacing-lg);
  border-radius: var(--radius-md);
}

.page-title {
  margin: 0;
  font-size: var(--font-size-2xl);
  font-weight: 600;
  color: var(--text-primary);
}

@media (max-width: 768px) {
  .header-section {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--spacing-md);
  }
}
</style>

