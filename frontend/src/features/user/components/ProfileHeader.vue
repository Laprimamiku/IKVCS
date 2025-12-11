<template>
  <div class="profile-header">
    <div class="back-btn" @click="$emit('back')">
      <el-icon><ArrowLeft /></el-icon>
      <span>返回首页</span>
    </div>
    <div class="header-content">
      <h2 class="title">个人中心</h2>
      <p class="subtitle">管理你的个人信息</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ArrowLeft } from '@element-plus/icons-vue'

defineEmits<{
  back: []
}>()
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
    background: linear-gradient(135deg, var(--bili-pink) 0%, var(--bili-blue) 100%);
    color: #fff;
    border-radius: 16px 16px 0 0;
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

