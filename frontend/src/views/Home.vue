<template>
  <div class="home-container">
    <!-- 顶部导航栏 -->
    <el-header class="header">
      <div class="header-content">
        <div class="logo">
          <h1>IKVCS</h1>
          <span>智能知识型视频社区</span>
        </div>
        
        <div class="user-info">
          <!-- 已登录 -->
          <template v-if="userStore.isLoggedIn">
            <el-avatar :src="userStore.avatar" />
            <span class="nickname">{{ userStore.nickname }}</span>
            <el-button type="danger" plain @click="handleLogout">
              登出
            </el-button>
          </template>
          
          <!-- 未登录 -->
          <template v-else>
            <el-button type="primary" @click="router.push('/login')">
              登录
            </el-button>
            <el-button @click="router.push('/register')">
              注册
            </el-button>
          </template>
        </div>
      </div>
    </el-header>

    <!-- 主要内容区域 -->
    <el-main class="main-content">
      <el-card class="welcome-card">
        <h2>欢迎来到 IKVCS</h2>
        <p>智能知识型视频社区系统</p>
        
        <div class="features">
          <el-row :gutter="20">
            <el-col :span="8">
              <div class="feature-item">
                <el-icon :size="40" color="#409eff"><VideoPlay /></el-icon>
                <h3>视频分片上传</h3>
                <p>支持大文件上传、秒传、断点续传</p>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="feature-item">
                <el-icon :size="40" color="#67c23a"><ChatDotRound /></el-icon>
                <h3>实时弹幕</h3>
                <p>WebSocket + Redis 实时推送</p>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="feature-item">
                <el-icon :size="40" color="#e6a23c"><MagicStick /></el-icon>
                <h3>AI 智能评分</h3>
                <p>LLM 对内容进行价值评分</p>
              </div>
            </el-col>
          </el-row>
        </div>

        <div class="status-info">
          <el-alert
            v-if="userStore.isLoggedIn"
            title="登录成功"
            type="success"
            :description="`欢迎回来，${userStore.nickname}！`"
            show-icon
            :closable="false"
          />
          <el-alert
            v-else
            title="未登录"
            type="info"
            description="请先登录以使用完整功能"
            show-icon
            :closable="false"
          />
        </div>
      </el-card>
    </el-main>
  </div>
</template>

<script setup>
/**
 * 首页
 * 
 * 功能：
 * 1. 显示欢迎信息
 * 2. 显示登录状态
 * 3. 提供登录/登出功能
 * 
 * 类比 Java：
 *   相当于 Spring MVC 的 HomeController + JSP 页面
 */
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { VideoPlay, ChatDotRound, MagicStick } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'

// 路由
const router = useRouter()

// 用户状态管理
const userStore = useUserStore()

/**
 * 页面加载时初始化用户信息
 * 
 * 为什么需要这个：
 *   页面刷新后，localStorage 中还有令牌
 *   需要重新获取用户信息，恢复登录状态
 */
onMounted(async () => {
  if (userStore.token && !userStore.userInfo) {
    try {
      await userStore.initUserInfo()
    } catch (error) {
      console.error('初始化用户信息失败:', error)
    }
  }
})

/**
 * 处理登出
 * 
 * 流程：
 * 1. 弹出确认对话框
 * 2. 用户确认后调用登出 API
 * 3. 登出成功后刷新页面
 */
const handleLogout = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要登出吗？',
      '提示',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    // 调用登出 API
    await userStore.logout()
    
    ElMessage.success('登出成功')
    
    // 刷新页面
    router.go(0)
  } catch (error) {
    if (error !== 'cancel') {
      console.error('登出失败:', error)
    }
  }
}
</script>

<style scoped>
/**
 * 样式说明：
 * 
 * 1. 使用 Element Plus 的布局组件
 * 2. 简洁的卡片式设计
 * 3. 响应式布局
 */

.home-container {
  min-height: 100vh;
  background: #f5f7fa;
}

.header {
  background: #fff;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  padding: 0;
}

.header-content {
  max-width: 1200px;
  margin: 0 auto;
  height: 100%;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 20px;
}

.logo {
  display: flex;
  align-items: baseline;
  gap: 10px;
}

.logo h1 {
  margin: 0;
  font-size: 24px;
  color: #409eff;
}

.logo span {
  font-size: 14px;
  color: #909399;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 15px;
}

.nickname {
  font-size: 14px;
  color: #606266;
}

.main-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 40px 20px;
}

.welcome-card {
  text-align: center;
}

.welcome-card h2 {
  margin: 0 0 10px 0;
  font-size: 32px;
  color: #303133;
}

.welcome-card > p {
  margin: 0 0 40px 0;
  font-size: 16px;
  color: #909399;
}

.features {
  margin: 40px 0;
}

.feature-item {
  padding: 20px;
  text-align: center;
}

.feature-item h3 {
  margin: 15px 0 10px 0;
  font-size: 18px;
  color: #303133;
}

.feature-item p {
  margin: 0;
  font-size: 14px;
  color: #909399;
}

.status-info {
  margin-top: 40px;
}
</style>
