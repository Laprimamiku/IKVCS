<template>
  <div class="filter-section">
    <el-radio-group :model-value="modelValue" @update:model-value="$emit('update:modelValue', $event)">
      <el-radio-button :label="null">全部</el-radio-button>
      <el-radio-button :label="0">转码中</el-radio-button>
      <el-radio-button :label="1">审核中</el-radio-button>
      <el-radio-button :label="2">已发布</el-radio-button>
      <el-radio-button :label="3">已拒绝</el-radio-button>
    </el-radio-group>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  modelValue: number | null
}>()

defineEmits<{
  'update:modelValue': [value: number | null]
}>()
</script>

<style lang="scss" scoped>
.filter-section {
  margin-bottom: var(--spacing-lg);
  background: var(--bg-white);
  padding: var(--spacing-md);
  border-radius: var(--radius-md);
}
</style>

