<template>
  <nav class="bili-category-nav">
    <div class="nav-container">
      <!-- All/Recommend Tab -->
      <div
        class="nav-item"
        :class="{ active: active === null }"
        @click="$emit('select', null)"
      >
        <el-icon class="nav-icon"><HomeFilled /></el-icon>
        <span>推荐</span>
      </div>
      
      <!-- Category Tabs -->
      <div
        v-for="cat in categories"
        :key="cat.id"
        class="nav-item"
        :class="{ active: active === cat.id }"
        @click="$emit('select', cat.id)"
      >
        <span>{{ cat.name }}</span>
      </div>
      
      <!-- More Button (if needed) -->
      <div class="nav-more" v-if="categories.length > 10">
        <el-icon><More /></el-icon>
      </div>
    </div>
    
    <!-- Active Indicator -->
    <div class="nav-indicator" :style="indicatorStyle"></div>
  </nav>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, nextTick } from "vue";
import { HomeFilled, More } from "@element-plus/icons-vue";

const props = defineProps<{
  categories: Array<{ id: number; name: string }>;
  active?: number | null;
}>();

const emit = defineEmits<{
  select: [id: number | null];
}>();

// Indicator position (for animation)
const indicatorStyle = ref({});

// Update indicator position when active changes
const updateIndicator = async () => {
  await nextTick();
  const activeEl = document.querySelector('.bili-category-nav .nav-item.active') as HTMLElement;
  if (activeEl) {
    indicatorStyle.value = {
      left: `${activeEl.offsetLeft}px`,
      width: `${activeEl.offsetWidth}px`,
    };
  }
};

watch(() => props.active, updateIndicator);
onMounted(updateIndicator);
</script>

<style lang="scss" scoped>
.bili-category-nav {
  position: sticky;
  top: var(--header-height);
  z-index: calc(var(--z-sticky) - 1);
  background: var(--bg-white);
  border-bottom: 1px solid var(--border-light);
  box-shadow: var(--shadow-sm);
}

.nav-container {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  max-width: var(--container-max-width);
  margin: 0 auto;
  padding: 0 var(--content-padding);
  overflow-x: auto;
  scrollbar-width: none;
  -ms-overflow-style: none;
  
  &::-webkit-scrollbar {
    display: none;
  }
}

.nav-item {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-3) var(--space-4);
  font-size: var(--font-size-base);
  color: var(--text-secondary);
  white-space: nowrap;
  cursor: pointer;
  border-radius: var(--radius-md);
  transition: all var(--transition-fast);
  position: relative;
  
  .nav-icon {
    font-size: 16px;
  }
  
  &:hover {
    color: var(--bili-pink);
    background: var(--bg-hover);
  }
  
  &.active {
    color: var(--bili-pink);
    font-weight: var(--font-weight-medium);
    
    &::after {
      content: "";
      position: absolute;
      bottom: 0;
      left: 50%;
      transform: translateX(-50%);
      width: 24px;
      height: 3px;
      background: var(--bili-pink);
      border-radius: 2px 2px 0 0;
    }
  }
}

.nav-more {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-2);
  color: var(--text-tertiary);
  cursor: pointer;
  border-radius: var(--radius-md);
  transition: var(--transition-fast);
  
  &:hover {
    color: var(--bili-pink);
    background: var(--bg-hover);
  }
}

/* Responsive */
@media (max-width: 768px) {
  .nav-container {
    padding: 0 var(--content-padding-mobile);
    gap: 0;
  }
  
  .nav-item {
    padding: var(--space-3) var(--space-3);
    font-size: var(--font-size-sm);
  }
}
</style>
