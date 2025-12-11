<template>
  <el-steps :active="active" align-center finish-status="success">
    <el-step title="选择文件" />
    <el-step title="填写信息" />
    <el-step title="上传完成" />
  </el-steps>
</template>

<script setup lang="ts">
defineProps<{
  active: number
}>()
</script>

<style lang="scss" scoped>
// 步骤指示器样式由 Element Plus 提供
</style>

