<template>
  <div class="filter-section">
    <el-radio-group :model-value="displayValue" @change="handleChange">
      <el-radio-button label="">全部</el-radio-button>
      <el-radio-button label="0">转码中</el-radio-button>
      <el-radio-button label="1">审核中</el-radio-button>
      <el-radio-button label="2">已发布</el-radio-button>
      <el-radio-button label="3">已拒绝</el-radio-button>
    </el-radio-group>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{
  modelValue: number | null;
}>();

const emit = defineEmits<{
  "update:modelValue": [value: number | null];
}>();

// 将 number | null 转换为字符串用于显示
const displayValue = computed(() => {
  return props.modelValue === null ? "" : String(props.modelValue);
});

// 处理变化，将字符串转换回 number | null
// 注意：这里必须接受 undefined，因为 Element Plus 的类型定义包含 undefined
const handleChange = (value: string | number | boolean | undefined) => {
  // 处理 undefined、空字符串或 null
  if (value === undefined || value === "" || value === null) {
    emit("update:modelValue", null);
    return;
  }

  // 转换为字符串再解析为数字
  const strValue = String(value);
  if (strValue === "") {
    emit("update:modelValue", null);
  } else {
    const numValue = parseInt(strValue, 10);
    emit("update:modelValue", isNaN(numValue) ? null : numValue);
  }
};
</script>

<style lang="scss" scoped>
.filter-section {
  margin-bottom: var(--spacing-lg);
  background: var(--bg-white);
  padding: var(--spacing-md);
  border-radius: var(--radius-md);
}
</style>
