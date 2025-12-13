<template>
  <div class="profile-header">
    <!-- 返回 -->
    <div class="back-btn" @click="$emit('back')">
      <el-icon><ArrowLeft /></el-icon>
      <span>返回首页</span>
    </div>

    <!-- 头部主体 -->
    <div class="header-content">
      <div class="header-top">
        <div>
          <h2 class="title">个人中心</h2>
          <p class="subtitle">管理你的个人信息</p>
        </div>

        <!-- 下拉菜单 -->
        <el-dropdown trigger="click">
          <span class="dropdown-trigger">
            更多
            <el-icon><ArrowDown /></el-icon>
          </span>

          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item
                command="collections"
                @click="router.push('/collections')"
              >
                我的收藏
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ArrowLeft, ArrowDown } from "@element-plus/icons-vue";
import { useRouter } from "vue-router";

const router = useRouter();

defineEmits<{
  back: [];
}>();
</script>

<style lang="scss" scoped>
.profile-header {
  .back-btn {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 8px 16px;
    margin-bottom: 24px;
    background: #fff;
    border-radius: 20px;
    cursor: pointer;
    transition: all 0.3s;
    color: var(--bili-text-2);
    font-size: 14px;

    &:hover {
      background: var(--bili-pink);
      color: #fff;
      transform: translateX(-4px);
    }
  }

  .header-content {
    padding: 32px 40px;
    background: linear-gradient(
      135deg,
      var(--bili-pink) 0%,
      var(--bili-blue) 100%
    );
    color: #fff;
    border-radius: 16px 16px 0 0;
  }

  .header-top {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .dropdown-trigger {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    cursor: pointer;
    font-size: 14px;
    opacity: 0.9;

    &:hover {
      opacity: 1;
    }
  }

  .title {
    font-size: 28px;
    font-weight: bold;
    margin: 0 0 8px 0;
  }

  .subtitle {
    font-size: 14px;
    opacity: 0.9;
    margin: 0;
  }

  @media (max-width: 768px) {
    .header-content {
      padding: 24px;
    }

    .title {
      font-size: 24px;
    }
  }
}
</style>
