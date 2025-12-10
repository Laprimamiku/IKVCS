<template>
  <div class="search-info">
    <h2 class="search-title">
      <template v-if="keyword">
        搜索结果：<span class="keyword">{{ keyword }}</span>
      </template>
      <template v-else> 全部视频 </template>
    </h2>
    <div class="search-meta">
      <span v-if="total > 0">找到 {{ total }} 个结果</span>
      <span v-else>暂无结果</span>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  keyword: string
  total: number
}>()
</script>

<style lang="scss" scoped>
.search-info {
  margin-bottom: var(--spacing-lg);
}

.search-title {
  font-size: var(--font-size-2xl);
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 var(--spacing-sm) 0;
}

.keyword {
  color: var(--primary-color);
}

.search-meta {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}
</style>

