<template>
  <div class="creator-sidebar">
    <div 
      class="sidebar-item" 
      :class="{ active: activeTab === 'videos' }"
      @click="$emit('tab-change', 'videos')"
    >
      <el-icon class="item-icon"><VideoCamera /></el-icon>
      <span class="item-text">视频管理</span>
    </div>

    <div 
      class="sidebar-item" 
      :class="{ active: activeTab === 'data' }"
      @click="$emit('tab-change', 'data')"
    >
      <el-icon class="item-icon"><DataAnalysis /></el-icon>
      <span class="item-text">数据中心</span>
    </div>

    <div 
      class="sidebar-item" 
      :class="{ active: activeTab === 'interaction' }"
      @click="$emit('tab-change', 'interaction')"
    >
      <el-icon class="item-icon"><ChatDotRound /></el-icon>
      <span class="item-text">互动管理</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { VideoCamera, DataAnalysis, ChatDotRound } from "@element-plus/icons-vue";

defineProps<{
  activeTab: 'videos' | 'data' | 'interaction';
}>();

defineEmits<{
  'tab-change': [tab: 'videos' | 'data' | 'interaction'];
}>();
</script>

<style lang="scss" scoped>
.creator-sidebar {
  width: 200px;
  background: var(--bg-white);
  border-right: 1px solid var(--border-color);
  padding: var(--space-4);
  height: 100%;
  overflow-y: auto;
}

.sidebar-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-base);
  color: var(--text-secondary);
  margin-bottom: var(--space-2);
  
  &:hover {
    background: var(--bg-hover);
    color: var(--text-primary);
  }
  
  &.active {
    background: var(--bili-blue-light);
    color: var(--bili-blue);
    border-right: 3px solid var(--bili-blue);
    font-weight: var(--font-weight-medium);
  }
  
  .item-icon {
    font-size: var(--font-size-lg);
  }
  
  .item-text {
    font-size: var(--font-size-base);
  }
}
</style>

