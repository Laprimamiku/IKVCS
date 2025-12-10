<template>
  <nav class="category-nav">
    <div class="nav-wrapper">
      <div
        v-for="cat in categories"
        :key="cat.id ?? 'recommend'"
        class="nav-item"
        :class="{ 'is-active': active === cat.id }"
        @click="$emit('select', cat.id)"
      >
        <el-icon v-if="cat.icon"><component :is="cat.icon" /></el-icon>
        <span>{{ cat.name }}</span>
      </div>
    </div>
  </nav>
</template>

<script setup>
defineProps({
  categories: {
    type: Array,
    default: () => [],
  },
  active: {
    type: [Number, null],
    default: null,
  },
});

defineEmits(["select"]);
</script>

<style scoped>
.category-nav {
  background: var(--bg-white);
  border-bottom: 1px solid var(--border-light);
  position: sticky;
  top: var(--header-height);
  z-index: calc(var(--z-index-sticky) - 1);
}

.nav-wrapper {
  max-width: var(--container-max-width);
  margin: 0 auto;
  padding: 0 var(--spacing-lg);
  display: flex;
  gap: var(--spacing-2xl);
  overflow-x: auto;
  scrollbar-width: none;
}

.nav-wrapper::-webkit-scrollbar {
  display: none;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  padding: var(--spacing-md) 0;
  font-size: var(--font-size-base);
  color: var(--text-regular);
  cursor: pointer;
  position: relative;
  white-space: nowrap;
  transition: color var(--transition-fast);
}

.nav-item:hover {
  color: var(--primary-color);
}

.nav-item.is-active {
  color: var(--primary-color);
  font-weight: 500;
}

.nav-item.is-active::after {
  content: "";
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: var(--primary-color);
  border-radius: var(--radius-sm) var(--radius-sm) 0 0;
}

@media (max-width: 768px) {
  .nav-wrapper {
    padding: 0 var(--spacing-md);
    gap: var(--spacing-lg);
  }
}
</style>

