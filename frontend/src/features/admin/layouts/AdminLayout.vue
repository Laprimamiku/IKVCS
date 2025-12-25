<template>
  <div class="bili-admin-layout" :class="{ 'sidebar-collapsed': sidebarCollapsed }">
    <!-- Sidebar -->
    <aside class="admin-sidebar">
      <div class="sidebar-header">
        <div class="logo-wrap">
          <span class="logo-icon">🎬</span>
          <transition name="fade">
            <span v-if="!sidebarCollapsed" class="logo-text">IKVCS 管理后台</span>
          </transition>
        </div>
        <button class="collapse-btn" @click="toggleSidebar">
          <span class="collapse-icon">{{ sidebarCollapsed ? '→' : '←' }}</span>
        </button>
      </div>

      <nav class="sidebar-nav">
        <div class="nav-section">
          <router-link to="/admin/dashboard" class="nav-item" active-class="active">
            <span class="nav-icon">📊</span>
            <span class="nav-text">数据中心</span>
          </router-link>
          
          <router-link to="/admin/audit" class="nav-item" active-class="active">
            <span class="nav-icon">🎥</span>
            <span class="nav-text">视频审核</span>
            <span v-if="pendingCount > 0" class="nav-badge">{{ pendingCount }}</span>
          </router-link>
          
          <router-link to="/admin/users" class="nav-item" active-class="active">
            <span class="nav-icon">👥</span>
            <span class="nav-text">用户管理</span>
          </router-link>
          
          <router-link to="/admin/reports" class="nav-item" active-class="active">
            <span class="nav-icon">⚠️</span>
            <span class="nav-text">举报处理</span>
          </router-link>
          
          <router-link to="/admin/categories" class="nav-item" active-class="active">
            <span class="nav-icon">📁</span>
            <span class="nav-text">分类管理</span>
          </router-link>
          
          <router-link to="/admin/ai" class="nav-item" active-class="active">
            <span class="nav-icon">🤖</span>
            <span class="nav-text">AI 控制台</span>
          </router-link>
        </div>

        <div class="nav-divider"></div>

        <div class="nav-section">
          <router-link to="/" class="nav-item">
            <span class="nav-icon">🏠</span>
            <span class="nav-text">返回主站</span>
          </router-link>
        </div>
      </nav>

      <div class="sidebar-footer">
        <div class="admin-avatar">
          <img :src="userStore.avatar || '/default-avatar.png'" alt="avatar" />
        </div>
        <transition name="fade">
          <div v-if="!sidebarCollapsed" class="admin-info">
            <span class="admin-name">{{ userStore.userInfo?.nickname }}</span>
            <span class="admin-role">管理员</span>
          </div>
        </transition>
      </div>
    </aside>

    <!-- Main Content -->
    <main class="admin-main">
      <!-- Header -->
      <header class="admin-header">
        <div class="header-left">
          <h1 class="page-title">{{ currentRouteName }}</h1>
          <div class="breadcrumb">
            <span class="crumb">管理后台</span>
            <span class="crumb-sep">/</span>
            <span class="crumb active">{{ currentRouteName }}</span>
          </div>
        </div>

        <div class="header-right">
          <div class="header-actions">
            <button class="action-btn" title="刷新">
              <span class="action-icon">🔄</span>
            </button>
            <button class="action-btn" title="通知">
              <span class="action-icon">🔔</span>
              <span v-if="pendingCount > 0" class="action-badge"></span>
            </button>
          </div>
          
          <div class="header-time">
            {{ currentTime }}
          </div>
        </div>
      </header>

      <!-- Content -->
      <div class="admin-content">
        <router-view v-slot="{ Component }">
          <transition name="page-fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted } from "vue";
import { useRoute } from "vue-router";
import { useUserStore } from "@/shared/stores/user";
import { adminApi } from "../api/admin.api";

const route = useRoute();
const userStore = useUserStore();
const pendingCount = ref(0);
const sidebarCollapsed = ref(false);
const currentTime = ref('');

const currentRouteName = computed(() => route.meta.title || "后台管理");

const toggleSidebar = () => {
  sidebarCollapsed.value = !sidebarCollapsed.value;
};

const updateTime = () => {
  const now = new Date();
  currentTime.value = now.toLocaleString('zh-CN', {
    month: 'numeric',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};

const fetchPendingCount = async () => {
  try {
    const res = await adminApi.getOverview();
    if (res.success && res.data) {
      pendingCount.value = res.data.total_reports_pending || 0;
    }
  } catch (e) {}
};

let timeInterval: number;

onMounted(() => {
  fetchPendingCount();
  updateTime();
  timeInterval = window.setInterval(updateTime, 60000);
});

onUnmounted(() => {
  clearInterval(timeInterval);
});
</script>

<style scoped lang="scss">
.bili-admin-layout {
  display: flex;
  min-height: 100vh;
  background: var(--bg-global);
}

/* Sidebar */
.admin-sidebar {
  width: 240px;
  background: var(--bg-white);
  border-right: 1px solid var(--border-light);
  display: flex;
  flex-direction: column;
  transition: width var(--transition-slow);
  position: fixed;
  left: 0;
  top: 0;
  bottom: 0;
  z-index: var(--z-fixed);

  .sidebar-collapsed & {
    width: 72px;
  }
}

.sidebar-header {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--space-4);
  border-bottom: 1px solid var(--border-light);
}

.logo-wrap {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  overflow: hidden;
}

.logo-icon {
  font-size: 24px;
  font-style: normal;
  flex-shrink: 0;
}

.logo-text {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-bold);
  color: var(--primary-color);
  white-space: nowrap;
}

.collapse-btn {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-gray-1);
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-base);
  flex-shrink: 0;

  &:hover {
    background: var(--bg-gray-2);
  }

  .collapse-icon {
    font-style: normal;
    font-size: var(--font-size-sm);
  }
}

/* Navigation */
.sidebar-nav {
  flex: 1;
  padding: var(--space-4) 0;
  overflow-y: auto;
}

.nav-section {
  padding: 0 var(--space-3);
}

.nav-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-3);
  margin-bottom: var(--space-1);
  color: var(--text-secondary);
  text-decoration: none;
  border-radius: var(--radius-md);
  transition: all var(--transition-base);
  position: relative;

  .nav-icon {
    font-size: var(--font-size-lg);
    font-style: normal;
    flex-shrink: 0;
    width: 24px;
    text-align: center;
  }

  .nav-text {
    font-size: var(--font-size-sm);
    white-space: nowrap;
    overflow: hidden;

    .sidebar-collapsed & {
      display: none;
    }
  }

  .nav-badge {
    margin-left: auto;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: var(--font-weight-medium);
    color: var(--text-white);
    background: var(--danger-color);
    border-radius: var(--radius-round);

    .sidebar-collapsed & {
      position: absolute;
      top: 4px;
      right: 4px;
      padding: 0;
      width: 8px;
      height: 8px;
    }
  }

  &:hover {
    background: var(--bg-hover);
    color: var(--text-primary);
  }

  &.active {
    background: var(--primary-light);
    color: var(--primary-color);
    font-weight: var(--font-weight-medium);

    &::before {
      content: '';
      position: absolute;
      left: 0;
      top: 50%;
      transform: translateY(-50%);
      width: 3px;
      height: 20px;
      background: var(--primary-color);
      border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
    }
  }
}

.nav-divider {
  height: 1px;
  background: var(--border-light);
  margin: var(--space-3) var(--space-4);
}

/* Sidebar Footer */
.sidebar-footer {
  padding: var(--space-4);
  border-top: 1px solid var(--border-light);
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.admin-avatar {
  width: 40px;
  height: 40px;
  flex-shrink: 0;

  img {
    width: 100%;
    height: 100%;
    border-radius: var(--radius-circle);
    object-fit: cover;
  }
}

.admin-info {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.admin-name {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.admin-role {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
}

/* Main Content */
.admin-main {
  flex: 1;
  margin-left: 240px;
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  transition: margin-left var(--transition-slow);

  .sidebar-collapsed & {
    margin-left: 72px;
  }
}

/* Header */
.admin-header {
  height: 64px;
  background: var(--bg-white);
  border-bottom: 1px solid var(--border-light);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--space-6);
  position: sticky;
  top: 0;
  z-index: var(--z-sticky);
}

.header-left {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.page-title {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
  margin: 0;
}

.breadcrumb {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
}

.crumb-sep {
  color: var(--text-quaternary);
}

.crumb.active {
  color: var(--text-secondary);
}

.header-right {
  display: flex;
  align-items: center;
  gap: var(--space-4);
}

.header-actions {
  display: flex;
  gap: var(--space-2);
}

.action-btn {
  position: relative;
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-gray-1);
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-base);

  .action-icon {
    font-size: var(--font-size-lg);
    font-style: normal;
  }

  .action-badge {
    position: absolute;
    top: 6px;
    right: 6px;
    width: 8px;
    height: 8px;
    background: var(--danger-color);
    border-radius: var(--radius-circle);
  }

  &:hover {
    background: var(--bg-gray-2);
  }
}

.header-time {
  font-size: var(--font-size-sm);
  color: var(--text-tertiary);
}

/* Content */
.admin-content {
  flex: 1;
  padding: var(--space-6);
  overflow-y: auto;
}

/* Transitions */
.fade-enter-active,
.fade-leave-active {
  transition: opacity var(--transition-base);
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.page-fade-enter-active,
.page-fade-leave-active {
  transition: all var(--transition-base);
}

.page-fade-enter-from {
  opacity: 0;
  transform: translateY(10px);
}

.page-fade-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

/* Responsive */
@media (max-width: 992px) {
  .admin-sidebar {
    width: 72px;
  }

  .admin-main {
    margin-left: 72px;
  }

  .nav-text,
  .logo-text,
  .admin-info {
    display: none !important;
  }
}
</style>
