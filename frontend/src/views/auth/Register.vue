<template>
  <div class="register-container">
    <el-card class="register-card">
      <template #header>
        <div class="card-header">
          <h2>用户注册</h2>
          <p>IKVCS - 智能知识型视频社区</p>
        </div>
      </template>

      <!-- 注册表单 -->
      <el-form
        ref="registerFormRef"
        :model="registerForm"
        :rules="registerRules"
        label-width="80px"
        size="large"
      >
        <!-- 用户名 -->
        <el-form-item label="用户名" prop="username">
          <el-input
            v-model="registerForm.username"
            placeholder="请输入用户名（3-50个字符）"
            prefix-icon="User"
            clearable
          />
        </el-form-item>

        <!-- 昵称 -->
        <el-form-item label="昵称" prop="nickname">
          <el-input
            v-model="registerForm.nickname"
            placeholder="请输入昵称（2-50个字符）"
            prefix-icon="Avatar"
            clearable
          />
        </el-form-item>

        <!-- 密码 -->
        <el-form-item label="密码" prop="password">
          <el-input
            v-model="registerForm.password"
            type="password"
            placeholder="请输入密码（至少6个字符）"
            prefix-icon="Lock"
            show-password
          />
        </el-form-item>

        <!-- 确认密码 -->
        <el-form-item label="确认密码" prop="confirmPassword">
          <el-input
            v-model="registerForm.confirmPassword"
            type="password"
            placeholder="请再次输入密码"
            prefix-icon="Lock"
            show-password
            @keyup.enter="handleRegister"
          />
        </el-form-item>

        <!-- 注册按钮 -->
        <el-form-item>
          <el-button
            type="primary"
            :loading="loading"
            style="width: 100%"
            @click="handleRegister"
          >
            {{ loading ? '注册中...' : '注册' }}
          </el-button>
        </el-form-item>

        <!-- 登录链接 -->
        <el-form-item>
          <div class="login-link">
            已有账号？
            <router-link to="/login">立即登录</router-link>
          </div>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
/**
 * 注册页面
 * 
 * 功能：
 * 1. 用户注册表单
 * 2. 表单验证（包括密码确认）
 * 3. 注册成功后自动登录并跳转
 * 
 * 类比 Java：
 *   相当于 Spring MVC 的 RegisterController + JSP 页面
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
const registerFormRef = ref(null)

// 加载状态
const loading = ref(false)

// 注册表单数据
const registerForm = reactive({
  username: '',
  nickname: '',
  password: '',
  confirmPassword: ''
})

/**
 * 自定义验证规则：确认密码
 * 
 * 为什么需要这个：
 *   确保用户两次输入的密码一致
 *   避免用户输错密码
 */
const validateConfirmPassword = (rule, value, callback) => {
  if (value === '') {
    callback(new Error('请再次输入密码'))
  } else if (value !== registerForm.password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

/**
 * 自定义验证规则：用户名格式
 * 
 * 为什么需要这个：
 *   用户名只能包含字母、数字、下划线
 *   与后端验证规则保持一致
 */
const validateUsername = (rule, value, callback) => {
  const usernameRegex = /^[a-zA-Z0-9_]+$/
  if (!usernameRegex.test(value)) {
    callback(new Error('用户名只能包含字母、数字、下划线'))
  } else {
    callback()
  }
}

// 表单验证规则
const registerRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 50, message: '用户名长度在 3 到 50 个字符', trigger: 'blur' },
    { validator: validateUsername, trigger: 'blur' }
  ],
  nickname: [
    { required: true, message: '请输入昵称', trigger: 'blur' },
    { min: 2, max: 50, message: '昵称长度在 2 到 50 个字符', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 50, message: '密码长度在 6 到 50 个字符', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请再次输入密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' }
  ]
}

/**
 * 处理注册
 * 
 * 流程：
 * 1. 验证表单
 * 2. 调用注册 API
 * 3. 注册成功后自动登录并跳转到首页
 * 4. 注册失败显示错误消息
 */
const handleRegister = async () => {
  // 1. 验证表单
  if (!registerFormRef.value) return
  
  await registerFormRef.value.validate(async (valid) => {
    if (!valid) {
      return false
    }

    // 2. 调用注册 API
    loading.value = true
    try {
      await userStore.register(
        registerForm.username,
        registerForm.password,
        registerForm.nickname
      )
      
      // 3. 注册成功（自动登录）
      ElMessage.success('注册成功！')
      
      // 跳转到首页
      router.push('/')
    } catch (error) {
      // 4. 注册失败
      console.error('注册失败:', error)
      const errorMsg = error.response?.data?.detail || '注册失败，请稍后重试'
      ElMessage.error(errorMsg)
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
 * 1. 与登录页面保持一致的设计风格
 * 2. 使用 Flexbox 居中布局
 * 3. 响应式设计
 */

.register-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.register-card {
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

.login-link {
  text-align: center;
  width: 100%;
  color: #606266;
  font-size: 14px;
}

.login-link a {
  color: #409eff;
  text-decoration: none;
}

.login-link a:hover {
  text-decoration: underline;
}
</style>
