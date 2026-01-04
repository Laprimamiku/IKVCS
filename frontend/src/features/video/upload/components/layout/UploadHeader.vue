<template>
  <div class="creator-header">
    <div class="header-container">
      <div class="header-left">
        <div class="logo-section">
          <el-icon class="logo-icon"><VideoCamera /></el-icon>
          <span class="logo-text">bilibili创作中心</span>
        </div>
        <div class="nav-tabs">
          <div class="nav-tab active">投稿管理</div>
          <div class="nav-tab">专栏管理</div>
          <div class="nav-tab">互动视频管理</div>
          <div class="nav-tab">合集管理</div>
          <div class="nav-tab">站内管理</div>
          <div class="nav-tab">视频素材管理</div>
        </div>
      </div>
      <div class="header-right">
        <div class="search-box">
          <input type="text" placeholder="搜索内容" class="search-input" />
          <button class="search-btn">
            <el-icon><Search /></el-icon>
          </button>
        </div>
        <div class="user-info">
          <span class="username">用户名</span>
          <el-avatar :size="32" class="user-avatar">
            <el-icon><User /></el-icon>
          </el-avatar>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { VideoCamera, Search, User } from "@element-plus/icons-vue";
</script>

<style lang="scss" scoped>
.creator-header {
  background: #fff;
  border-bottom: 1px solid #e3e5e7;
  position: sticky;
  top: 0;
  z-index: 100;
}

.header-container {
  max-width: 1400px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  height: 64px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 40px;
}

.logo-section {
  display: flex;
  align-items: center;
  gap: 8px;
  
  .logo-icon {
    font-size: 24px;
  }
  
  .logo-text {
    font-size: 18px;
    font-weight: 600;
    color: #18191c;
  }
}

.nav-tabs {
  display: flex;
  align-items: center;
  gap: 32px;
}

.nav-tab {
  padding: 8px 0;
  font-size: 14px;
  color: #61666d;
  cursor: pointer;
  position: relative;
  transition: color 0.2s;
  
  &:hover {
    color: #00aeec;
  }
  
  &.active {
    color: #00aeec;
    font-weight: 500;
    
    &::after {
      content: '';
      position: absolute;
      bottom: -1px;
      left: 0;
      right: 0;
      height: 2px;
      background: #00aeec;
    }
  }
}

.header-right {
  display: flex;
  align-items: center;
  gap: 24px;
}

.search-box {
  display: flex;
  align-items: center;
  background: #f1f2f3;
  border-radius: 20px;
  padding: 0 16px;
  height: 36px;
  
  .search-input {
    border: none;
    background: none;
    outline: none;
    font-size: 14px;
    width: 200px;
    
    &::placeholder {
      color: #9499a0;
    }
  }
  
  .search-btn {
    border: none;
    background: none;
    cursor: pointer;
    color: #9499a0;
    font-size: 16px;
  }
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  
  .username {
    font-size: 14px;
    color: #18191c;
  }
  
  .user-avatar {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: #00aeec;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-size: 16px;
  }
}

@media (max-width: 1200px) {
  .header-container {
    padding: 0 16px;
  }
  
  .nav-tabs {
    gap: 24px;
  }
}

@media (max-width: 768px) {
  .header-left {
    gap: 20px;
  }
  
  .nav-tabs {
    display: none;
  }
  
  .search-box .search-input {
    width: 150px;
  }
}
</style>

