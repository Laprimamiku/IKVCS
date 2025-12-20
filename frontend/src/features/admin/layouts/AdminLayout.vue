<template>
  <div class="admin-layout">
    <aside class="admin-sidebar">
      <div class="logo-area">
        <h1 class="logo-text">IKVCS 管理后台</h1>
      </div>
      <nav class="nav-menu">
        <router-link
          to="/admin/dashboard"
          class="nav-item"
          active-class="active"
        >
          <i class="iconfont icon-dashboard"></i> 数据中心
        </router-link>
        <router-link to="/admin/audit" class="nav-item" active-class="active">
          <i class="iconfont icon-audit"></i> 视频审核
          <span v-if="pendingCount > 0" class="badge">{{ pendingCount }}</span>
        </router-link>
        <router-link to="/admin/users" class="nav-item" active-class="active">
          <i class="iconfont icon-users"></i> 用户管理
        </router-link>
        <router-link to="/admin/reports" class="nav-item" active-class="active">
          <i class="iconfont icon-report"></i> 举报处理
        </router-link>
        <router-link
          to="/admin/categories"
          class="nav-item"
          active-class="active"
        >
          <i class="iconfont icon-category"></i> 分类管理
        </router-link>

        <router-link
          to="/admin/ai"
          class="nav-item"
          :class="{ active: $route.path.startsWith('/admin/ai') }"
        >
          <i class="icon-brain"></i> <span>AI 进化控制台</span>
        </router-link>

        <div class="nav-divider"></div>
        <router-link to="/" class="nav-item">
          <i class="iconfont icon-home"></i> 返回主站
        </router-link>
      </nav>
    </aside>

    <main class="admin-content">
      <header class="admin-header">
        <div class="breadcrumb">
          {{ currentRouteName }}
        </div>
        <div class="user-info">
          <span>管理员: {{ userStore.userInfo?.nickname }}</span>
        </div>
      </header>
      <div class="content-wrapper">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted } from "vue";
import { useRoute } from "vue-router";
import { useUserStore } from "@/shared/stores/user";
import { adminApi } from "../api/admin.api";

const route = useRoute();
const userStore = useUserStore();
const pendingCount = ref(0);

const currentRouteName = computed(() => route.meta.title || "后台管理");

// 简单轮询一下待审核数量用于展示徽标
const fetchPendingCount = async () => {
  try {
    const res = await adminApi.getOverview();
    // @ts-ignore
    pendingCount.value = res.total_reports_pending; // 这里用举报数或待审核视频数
  } catch (e) {}
};

onMounted(() => {
  fetchPendingCount();
});
</script>

<style scoped lang="scss">
.admin-layout {
  display: flex;
  height: 100vh;
  background-color: #f4f5f7;
  color: #18191c;
}

.admin-sidebar {
  width: 240px;
  background: #fff;
  border-right: 1px solid #e7e7e7;
  display: flex;
  flex-direction: column;

  .logo-area {
    height: 60px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-bottom: 1px solid #f0f0f0;

    .logo-text {
      font-size: 20px;
      color: var(--primary-color); // Bilibili Pink
      font-weight: bold;
    }
  }

  .nav-menu {
    padding: 16px 0;
    flex: 1;

    .nav-item {
      display: flex;
      align-items: center;
      padding: 0 24px;
      height: 48px;
      color: #61666d;
      text-decoration: none;
      font-size: 14px;
      transition: all 0.2s;
      position: relative;

      &:hover {
        background-color: #f4f5f7;
        color: #18191c;
      }

      &.active {
        color: var(--primary-color);
        background-color: rgba(251, 114, 153, 0.1);
        border-right: 3px solid var(--primary-color);
      }

      .iconfont {
        margin-right: 12px;
        font-size: 18px;
      }

      .badge {
        margin-left: auto;
        background: #f56c6c;
        color: #fff;
        font-size: 12px;
        padding: 2px 6px;
        border-radius: 10px;
        line-height: 1;
      }
    }

    .nav-divider {
      height: 1px;
      background: #e7e7e7;
      margin: 12px 24px;
    }
  }
}

.admin-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;

  .admin-header {
    height: 60px;
    background: #fff;
    border-bottom: 1px solid #e7e7e7;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 32px;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);

    .breadcrumb {
      font-size: 16px;
      color: #18191c;
      font-weight: 500;
    }

    .user-info {
      font-size: 14px;
      color: #61666d;
    }
  }

  .content-wrapper {
    flex: 1;
    overflow-y: auto;
    padding: 24px;
  }
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
