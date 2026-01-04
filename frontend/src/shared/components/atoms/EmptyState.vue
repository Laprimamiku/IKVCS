<template>
  <div class="empty-state" :class="{ [size]: size }">
    <div class="empty-icon" v-if="$slots.icon || icon">
      <slot name="icon">
        <el-icon v-if="icon" :size="iconSize"><component :is="icon" /></el-icon>
      </slot>
    </div>
    <div class="empty-title" v-if="title || $slots.title">
      <slot name="title">{{ title }}</slot>
    </div>
    <div class="empty-description" v-if="description || $slots.description">
      <slot name="description">{{ description }}</slot>
    </div>
    <div class="empty-action" v-if="$slots.action">
      <slot name="action"></slot>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Component } from 'vue'

defineProps<{
  title?: string
  description?: string
  icon?: Component
  size?: 'small' | 'medium' | 'large'
  iconSize?: number
}>()
</script>

<style lang="scss" scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-8) var(--space-4);
  text-align: center;

  .empty-icon {
    margin-bottom: var(--space-4);
    color: var(--text-tertiary);
    opacity: 0.6;
  }

  .empty-title {
    font-size: var(--font-size-lg);
    font-weight: var(--font-weight-semibold);
    color: var(--text-primary);
    margin-bottom: var(--space-2);
  }

  .empty-description {
    font-size: var(--font-size-base);
    color: var(--text-secondary);
    margin-bottom: var(--space-4);
    max-width: 400px;
  }

  .empty-action {
    margin-top: var(--space-2);
  }

  // Sizes
  &.small {
    padding: var(--space-4);
    
    .empty-icon {
      margin-bottom: var(--space-2);
    }
    
    .empty-title {
      font-size: var(--font-size-base);
    }
    
    .empty-description {
      font-size: var(--font-size-sm);
    }
  }

  &.large {
    padding: var(--space-12) var(--space-6);
    
    .empty-icon {
      margin-bottom: var(--space-6);
    }
    
    .empty-title {
      font-size: var(--font-size-xl);
    }
    
    .empty-description {
      font-size: var(--font-size-lg);
    }
  }
}
</style>














