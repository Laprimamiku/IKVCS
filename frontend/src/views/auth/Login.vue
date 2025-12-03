<template>
  <div class="login-container">
    <el-card class="login-card">
      <template #header>
        <div class="card-header">
          <h2>用户登录</h2>
          <p>IKVCS - 智能知识型视频社区</p>
        </div>
      </template>

      <!-- 登录表单 -->
      <el-form
        ref="loginFormRef"
        :model="loginForm"
        :rules="loginRules"
        label-width="80px"
        size="large"
      >
        <!-- 用户名 -->
        <el-form-item label="用户名" prop="username">
          <el-input
            v-model="loginForm.username"
            placeholder="请输入用户名"
            prefix-icon="User"
            clearable
          />
        </el-form-item>

        <!-- 密码 -->
        <el-form-item label="密码" prop="password">
          <el-input
            v-model="loginForm.password"
            type="password"
            placeholder="请输入密码"
            prefix-icon="Lock"
            show-password
            @keyup.enter="handleLogin"
          />
        </el-form-item>

        <!-- 登录按钮 -->
        <el-form-item>
          <el-button
            type="primary"
            :loading="loading"
            style="width: 100%"
            @click="handleLogin"
          >
            {{ loading ? '登录中...' : '登录' }}
          </el-button>
        </el-form-item>

        <!-- 注册链接 -->
        <el-form-item>
          <div class="register-link">
            还没有账号？
            <router-link to="/register">立即注册</router-link>
          </div>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
/**
 * 登录页面
 * 
 * 功能：
 * 1. 用户登录表单
 * 2. 表单验证
 * 3. 登录成功后跳转
 * 
 * 类比 Java：
 *   相当于 Spring MVC 的 LoginController + JSP 页面
 */
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'

// 路由
const router = useRouter()

// 用户状态管理
const userStore = useUserStore()

// 表单引用
const loginFormRef = ref(null)

// 加载状态
const loading = ref(false)

// 登录表单数据
const loginForm = reactive({
  username: '',
  password: ''
})

// 表单验证规则
const loginRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 50, message: '用户名长度在 3 到 50 个字符', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 50, message: '密码长度在 6 到 50 个字符', trigger: 'blur' }
  ]
}

/**
 * 处理登录
 * 
 * 流程：
 * 1. 验证表单
 * 2. 调用登录 API
 * 3. 登录成功后跳转到首页
 * 4. 登录失败显示错误消息
 */
const handleLogin = async () => {
  // 1. 验证表单
  if (!loginFormRef.value) return
  
  await loginFormRef.value.validate(async (valid) => {
    if (!valid) {
      return false
    }

    // 2. 调用登录 API
    loading.value = true
    try {
      await userStore.login(loginForm.username, loginForm.password)
      
      // 3. 登录成功
      ElMessage.success('登录成功！')
      
      // 跳转到首页
      router.push('/')
    } catch (error) {
      // 4. 登录失败
      console.error('登录失败:', error)
      ElMessage.error(error.response?.data?.detail || '登录失败，请检查用户名和密码')
    } finally {
      loading.value = false
    }
  })
}
</script>

<style scoped>
/**
 * 样式说明：
 * 
 * 1. 使用 Flexbox 居中布局
 * 2. 卡片宽度固定，响应式设计
 * 3. 简洁的配色方案
 */

.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-card {
  width: 450px;
  max-width: 90%;
}

.card-header {
  text-align: center;
}

.card-header h2 {
  margin: 0 0 10px 0;
  color: #303133;
  font-size: 24px;
}

.card-header p {
  margin: 0;
  color: #909399;
  font-size: 14px;
}

.register-link {
  text-align: center;
  width: 100%;
  color: #606266;
  font-size: 14px;
}

.register-link a {
  color: #409eff;
  text-decoration: none;
}

.register-link a:hover {
  text-decoration: underline;
}
</style>
