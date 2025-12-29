<template>
  <div class="loading-state" :class="{ [size]: size, fullscreen: fullscreen }">
    <div class="loading-spinner" v-if="type === 'spinner'">
      <el-icon class="spinner-icon" :size="iconSize">
        <Loading />
      </el-icon>
    </div>
    <el-skeleton v-else-if="type === 'skeleton'" :rows="rows" animated />
    <div class="loading-text" v-if="text">
      {{ text }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { Loading } from '@element-plus/icons-vue'

defineProps<{
  type?: 'spinner' | 'skeleton'
  text?: string
  size?: 'small' | 'medium' | 'large'
  fullscreen?: boolean
  rows?: number
  iconSize?: number
}>()
</script>

<style lang="scss" scoped>
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-8);

  .loading-spinner {
    margin-bottom: var(--space-4);
    
    .spinner-icon {
      color: var(--bili-pink);
      animation: spin 1s linear infinite;
    }
  }

  .loading-text {
    font-size: var(--font-size-sm);
    color: var(--text-tertiary);
    margin-top: var(--space-2);
  }

  // Sizes
  &.small {
    padding: var(--space-4);
  }

  &.large {
    padding: var(--space-12);
  }

  // Fullscreen
  &.fullscreen {
    position: fixed;
    inset: 0;
    background: rgba(255, 255, 255, 0.9);
    z-index: var(--z-loading);
  }
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>

