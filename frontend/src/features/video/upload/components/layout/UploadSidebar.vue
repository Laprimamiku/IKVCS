<template>
  <div class="creator-sidebar">
    <div class="sidebar-section">
      <div class="section-title">
        <el-icon><DataAnalysis /></el-icon>
        <span>首页</span>
      </div>
      <div class="sidebar-item active">
        <el-icon class="item-icon"><Document /></el-icon>
        <span class="item-text">稿件管理</span>
      </div>
      <div class="sidebar-item">
        <el-icon class="item-icon"><DataAnalysis /></el-icon>
        <span class="item-text">数据中心</span>
      </div>
      <div class="sidebar-item">
        <el-icon class="item-icon"><Money /></el-icon>
        <span class="item-text">收益管理</span>
      </div>
    </div>

    <div class="sidebar-section">
      <div class="section-title">
        <el-icon><VideoCamera /></el-icon>
        <span>互动管理</span>
      </div>
      <div class="sidebar-item">
        <el-icon class="item-icon"><ChatDotRound /></el-icon>
        <span class="item-text">评论管理</span>
      </div>
      <div class="sidebar-item">
        <el-icon class="item-icon"><UserFilled /></el-icon>
        <span class="item-text">粉丝管理</span>
      </div>
    </div>

    <div class="sidebar-section">
      <div class="section-title">
        <el-icon><Setting /></el-icon>
        <span>创作助手</span>
      </div>
      <div class="sidebar-item">
        <el-icon class="item-icon"><Brush /></el-icon>
        <span class="item-text">创作中心</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import {
  DataAnalysis,
  Document,
  Money,
  VideoCamera,
  ChatDotRound,
  UserFilled,
  Setting,
  Brush,
} from "@element-plus/icons-vue";
</script>

<style lang="scss" scoped>
.creator-sidebar {
  width: 240px;
  background: #fff;
  border-right: 1px solid #e3e5e7;
  padding: 24px 0;
}

.sidebar-section {
  margin-bottom: 32px;
  
  &:last-child {
    margin-bottom: 0;
  }
}

.section-title {
  padding: 0 24px 12px;
  font-size: 12px;
  color: #9499a0;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.sidebar-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 24px;
  color: #61666d;
  cursor: pointer;
  transition: all 0.2s;
  
  &:hover {
    background: #f1f2f3;
    color: #18191c;
  }
  
  &.active {
    background: #e7f6ff;
    color: #00aeec;
    border-right: 3px solid #00aeec;
  }
  
  .item-icon {
    font-size: 16px;
  }
  
  .item-text {
    font-size: 14px;
    font-weight: 400;
  }
}

@media (max-width: 768px) {
  .creator-sidebar {
    display: none;
  }
}
</style>

