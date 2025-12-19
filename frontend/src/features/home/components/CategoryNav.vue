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

<script setup lang="ts">
defineProps<{
  categories: Array<any>
  active?: number | null
}>()

defineEmits<{
  select: [id: number | null]
}>()
</script>

<style lang="scss" scoped>
.category-nav {
  background: var(--bg-white);
  border-bottom: 1px solid var(--border-light);
  position: sticky;
  top: 64px;
  z-index: 999;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.02);
}

.nav-wrapper {
  max-width: var(--container-max-width);
  margin: 0 auto;
  padding: 0 24px;
  display: flex;
  gap: 32px;
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
  gap: 6px;
  padding: 14px 0;
  font-size: 14px;
  color: var(--text-secondary);
  cursor: pointer;
  position: relative;
  white-space: nowrap;
  transition: color 0.2s;
  font-weight: 400;

  .el-icon {
    font-size: 16px;
  }

  &:hover {
    color: var(--primary-color);
  }

  &.is-active {
    color: var(--primary-color);
    font-weight: 500;

    &::after {
      content: "";
      position: absolute;
      bottom: 0;
      left: 0;
      right: 0;
      height: 3px;
      background: var(--primary-color);
      border-radius: 2px 2px 0 0;
    }
  }
}

@media (max-width: 768px) {
  .nav-wrapper {
    padding: 0 16px;
    gap: 20px;
  }
}
</style>

