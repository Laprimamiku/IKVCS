<template>
  <div class="filter-bar">
    <div class="filter-section">
      <span class="filter-label">分类：</span>
      <div class="filter-options">
        <span
          class="filter-option"
          :class="{ 'is-active': modelValue === null }"
          @click="$emit('update:modelValue', null)"
        >
          全部
        </span>
        <span
          v-for="cat in categories"
          :key="cat.id"
          class="filter-option"
          :class="{ 'is-active': modelValue === cat.id }"
          @click="$emit('update:modelValue', cat.id)"
        >
          {{ cat.name }}
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Category } from '@/types/entity'

defineProps<{
  modelValue: number | null
  categories: Category[]
}>()

defineEmits<{
  'update:modelValue': [value: number | null]
}>()
</script>

<style lang="scss" scoped>
.filter-bar {
  background: var(--bg-white);
  border-radius: var(--radius-md);
  padding: var(--spacing-md);
  margin-bottom: var(--spacing-lg);
}

.filter-section {
  display: flex;
  align-items: flex-start;
  gap: var(--spacing-md);
}

.filter-label {
  font-size: var(--font-size-base);
  font-weight: 500;
  color: var(--text-regular);
  white-space: nowrap;
  padding-top: var(--spacing-xs);
}

.filter-options {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-sm);
  flex: 1;
}

.filter-option {
  padding: var(--spacing-xs) var(--spacing-md);
  background: var(--bg-light);
  border-radius: var(--radius-base);
  font-size: var(--font-size-sm);
  color: var(--text-regular);
  cursor: pointer;
  transition: all var(--transition-fast);
  user-select: none;
}

.filter-option:hover {
  background: var(--primary-light);
  color: var(--primary-color);
}

.filter-option.is-active {
  background: var(--primary-color);
  color: var(--text-white);
}

@media (max-width: 768px) {
  .filter-section {
    flex-direction: column;
    gap: var(--spacing-sm);
  }
}
</style>

