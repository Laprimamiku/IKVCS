<template>
  <div class="stat-card" :class="{ [variant]: variant }">
    <div class="stat-icon-wrapper" v-if="$slots.icon">
      <slot name="icon"></slot>
    </div>
    <div class="stat-content">
      <div class="stat-value">
        <slot name="value">{{ value }}</slot>
      </div>
      <div class="stat-label">
        <slot name="label">{{ label }}</slot>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  value?: string | number
  label?: string
  variant?: 'default' | 'primary' | 'success' | 'warning' | 'danger'
}>()
</script>

<style lang="scss" scoped>
.stat-card {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-4);
  background: var(--bg-white);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-card);
  transition: var(--transition-base);

  &:hover {
    transform: translateY(-2px);
    box-shadow: var(--shadow-md);
  }

  .stat-icon-wrapper {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 48px;
    height: 48px;
    border-radius: var(--radius-md);
    background: var(--bg-gray-1);
    color: var(--text-secondary);
    flex-shrink: 0;
  }

  .stat-content {
    flex: 1;
    min-width: 0;
  }

  .stat-value {
    font-size: var(--font-size-2xl);
    font-weight: var(--font-weight-bold);
    color: var(--text-primary);
    line-height: 1.2;
    margin-bottom: var(--space-1);
  }

  .stat-label {
    font-size: var(--font-size-sm);
    color: var(--text-tertiary);
  }

  // Variants
  &.primary .stat-icon-wrapper {
    background: var(--bili-pink-light);
    color: var(--bili-pink);
  }

  &.success .stat-icon-wrapper {
    background: var(--success-light);
    color: var(--success-color);
  }

  &.warning .stat-icon-wrapper {
    background: var(--warning-light);
    color: var(--warning-color);
  }

  &.danger .stat-icon-wrapper {
    background: var(--danger-light);
    color: var(--danger-color);
  }
}
</style>





