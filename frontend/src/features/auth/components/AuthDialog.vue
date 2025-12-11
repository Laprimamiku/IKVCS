<template>
  <el-dialog
    v-model="dialogVisible"
    :title="isLogin ? '登录' : '注册'"
    width="420px"
    :before-close="handleClose"
    class="auth-dialog"
  >
    <!-- 登录表单 -->
    <el-form
      v-if="isLogin"
      ref="loginFormRef"
      :model="loginForm"
      :rules="loginRules"
      class="auth-form"
      size="large"
    >
      <el-form-item prop="username">
        <el-input
          v-model="loginForm.username"
          placeholder="请输入用户名"
          prefix-icon="User"
          clearable
        />
      </el-form-item>

      <el-form-item prop="password">
        <el-input
          v-model="loginForm.password"
          type="password"
          placeholder="请输入密码"
          prefix-icon="Lock"
          show-password
          @keyup.enter="handleLogin"
        />
      </el-form-item>

      <el-form-item>
        <el-button
          type="primary"
          :loading="loading"
          class="auth-btn"
          @click="handleLogin"
        >
          {{ loading ? '登录中...' : '登录' }}
        </el-button>
      </el-form-item>

      <div class="auth-switch">
        <span>还没有账号？</span>
        <el-link type="primary" @click="switchMode">立即注册</el-link>
      </div>
    </el-form>

    <!-- 注册表单 -->
    <el-form
      v-else
      ref="registerFormRef"
      :model="registerForm"
      :rules="registerRules"
      class="auth-form"
      size="large"
    >
      <el-form-item prop="username">
        <el-input
          v-model="registerForm.username"
          placeholder="用户名（3-50个字符）"
          prefix-icon="User"
          clearable
        />
      </el-form-item>

      <el-form-item prop="nickname">
        <el-input
          v-model="registerForm.nickname"
          placeholder="昵称（2-50个字符）"
          prefix-icon="Avatar"
          clearable
        />
      </el-form-item>

      <el-form-item prop="password">
        <el-input
          v-model="registerForm.password"
          type="password"
          placeholder="密码（至少6个字符）"
          prefix-icon="Lock"
          show-password
        />
      </el-form-item>

      <el-form-item prop="confirmPassword">
        <el-input
          v-model="registerForm.confirmPassword"
          type="password"
          placeholder="确认密码"
          prefix-icon="Lock"
          show-password
          @keyup.enter="handleRegister"
        />
      </el-form-item>

      <el-form-item>
        <el-button
          type="primary"
          :loading="loading"
          class="auth-btn"
          @click="handleRegister"
        >
          {{ loading ? '注册中...' : '注册' }}
        </el-button>
      </el-form-item>

      <div class="auth-switch">
        <span>已有账号？</span>
        <el-link type="primary" @click="switchMode">立即登录</el-link>
      </div>
    </el-form>
  </el-dialog>
</template>

<script setup lang="ts">
/**
 * 登录注册弹窗组件
 * 
 * 功能：
 * 1. 登录表单
 * 2. 注册表单
 * 3. 表单切换
 */
import { ref, reactive, watch } from 'vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules, FormItemRule } from 'element-plus'
import { useUserStore } from "@/shared/stores/user"

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  mode: {
    type: String,
    default: 'login' // 'login' | 'register'
  }
})

const emit = defineEmits(['update:modelValue', 'success'])

const userStore = useUserStore()
const dialogVisible = ref(props.modelValue)
const isLogin = ref(props.mode === 'login')
const loading = ref(false)

const loginFormRef = ref<FormInstance | null>(null)
const registerFormRef = ref<FormInstance | null>(null)

// 登录表单
type LoginForm = {
  username: string
  password: string
}

const loginForm = reactive<LoginForm>({
  username: '',
  password: ''
})

// 注册表单
type RegisterForm = {
  username: string
  nickname: string
  password: string
  confirmPassword: string
}

const registerForm = reactive<RegisterForm>({
  username: '',
  nickname: '',
  password: '',
  confirmPassword: ''
})

// 登录验证规则
const loginRules: FormRules<LoginForm> = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 50, message: '用户名长度在 3 到 50 个字符', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 50, message: '密码长度在 6 到 50 个字符', trigger: 'blur' }
  ]
}

// 注册验证规则
const validateConfirmPassword: FormItemRule['validator'] = (_rule, value, callback) => {
  if (value === '') {
    callback(new Error('请再次输入密码'))
  } else if (value !== registerForm.password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const validateUsername: FormItemRule['validator'] = (_rule, value, callback) => {
  const usernameRegex = /^[a-zA-Z0-9_]+$/
  if (!usernameRegex.test(value)) {
    callback(new Error('用户名只能包含字母、数字、下划线'))
  } else {
    callback()
  }
}

const registerRules: FormRules<RegisterForm> = {
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

// 监听 modelValue 变化
watch(() => props.modelValue, (val) => {
  dialogVisible.value = val
})

// 监听 dialogVisible 变化
watch(dialogVisible, (val) => {
  emit('update:modelValue', val)
})

// 监听 mode 变化
watch(() => props.mode, (val) => {
  isLogin.value = val === 'login'
})

/**
 * 关闭对话框
 */
const handleClose = () => {
  dialogVisible.value = false
}

/**
 * 切换登录/注册模式
 */
const switchMode = () => {
  isLogin.value = !isLogin.value
}

/**
 * 处理登录
 */
const handleLogin = async () => {
  if (!loginFormRef.value) return

  const valid = await loginFormRef.value.validate()
  if (!valid) return

  loading.value = true
  try {
    await userStore.login(loginForm.username, loginForm.password)
    ElMessage.success('登录成功！')
    dialogVisible.value = false
    emit('success')
  } catch (error) {
    console.error('登录失败:', error)
    const errorMsg =
      (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
      '登录失败，请检查用户名和密码'
    ElMessage.error(errorMsg)
  } finally {
    loading.value = false
  }
}

/**
 * 处理注册
 */
const handleRegister = async () => {
  if (!registerFormRef.value) return

  const valid = await registerFormRef.value.validate()
  if (!valid) return

  loading.value = true
  try {
    await userStore.register(
      registerForm.username,
      registerForm.password,
      registerForm.nickname
    )
    
    ElMessage.success('注册成功！')
    dialogVisible.value = false
    emit('success')
  } catch (error) {
    console.error('注册失败:', error)
    const errorMsg =
      (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
      '注册失败，请稍后重试'
    ElMessage.error(errorMsg)
  } finally {
    loading.value = false
  }
}
</script>

<style lang="scss" scoped>
.auth-dialog :deep(.el-dialog__header) {
  text-align: center;
  padding: 24px 24px 16px;
  border-bottom: 1px solid var(--border-light);
}

.auth-dialog :deep(.el-dialog__title) {
  font-size: 20px;
  font-weight: bold;
  color: var(--text-primary);
}

.auth-dialog :deep(.el-dialog__body) {
  padding: 32px 40px;
}

.auth-form {
  margin-top: 0;
}

.auth-btn {
  width: 100%;
  height: 44px;
  font-size: 16px;
  font-weight: 600;
  background: #00a1d6;
  border: none;
  border-radius: 22px;
  color: #ffffff;
}

.auth-btn:hover {
  background: #00b5e5;
}

.auth-switch {
  text-align: center;
  margin-top: 16px;
  font-size: 14px;
  color: var(--text-regular);
}

.auth-switch .el-link {
  margin-left: 8px;
  font-weight: 500;
}
</style>
