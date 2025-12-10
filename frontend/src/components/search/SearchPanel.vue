<template>
  <div class="search-dropdown">
    <div v-if="searchHistory.length" class="search-section">
      <div class="section-header">
        <span>搜索历史</span>
        <el-button text size="small" @click="$emit('clear-history')">清空</el-button>
      </div>
      <div class="history-list">
        <span
          v-for="(item, index) in searchHistory"
          :key="index"
          class="history-item"
          @click="$emit('select-history', item)"
        >
          {{ item }}
        </span>
      </div>
    </div>

    <div class="search-section">
      <div class="section-header">
        <span>热搜榜</span>
      </div>
      <div class="trending-list">
        <div
          v-for="(item, index) in trendingSearches"
          :key="index"
          class="trending-item"
          @click="$emit('select-trending', item)"
        >
          <span class="rank" :class="{ 'rank-top': index < 3 }">
            {{ index + 1 }}
          </span>
          <span class="keyword">{{ item }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  searchHistory: {
    type: Array,
    default: () => [],
  },
  trendingSearches: {
    type: Array,
    default: () => [],
  },
});

defineEmits(["select-history", "select-trending", "clear-history"]);
</script>

<style scoped>
.search-dropdown {
  position: absolute;
  top: calc(100% + var(--spacing-sm));
  left: 0;
  right: 0;
  background: var(--bg-white);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  padding: var(--spacing-md);
  z-index: var(--z-index-dropdown);
  animation: fadeInUp 0.3s ease;
}

.search-section {
  margin-bottom: var(--spacing-md);
}

.search-section:last-child {
  margin-bottom: 0;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--spacing-sm);
  font-size: var(--font-size-sm);
  font-weight: 500;
  color: var(--text-regular);
}

.history-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-sm);
}

.history-item {
  padding: var(--spacing-xs) var(--spacing-base);
  background: var(--bg-light);
  border-radius: var(--radius-base);
  font-size: var(--font-size-sm);
  color: var(--text-regular);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.history-item:hover {
  background: var(--primary-light);
  color: var(--primary-color);
}

.trending-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.trending-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-xs) var(--spacing-sm);
  border-radius: var(--radius-base);
  cursor: pointer;
  transition: background var(--transition-fast);
}

.trending-item:hover {
  background: var(--bg-light);
}

.rank {
  width: 20px;
  text-align: center;
  font-size: var(--font-size-sm);
  font-weight: 500;
  color: var(--text-secondary);
}

.rank-top {
  color: var(--primary-color);
  font-weight: bold;
}

.keyword {
  flex: 1;
  font-size: var(--font-size-sm);
  color: var(--text-regular);
}
</style>

