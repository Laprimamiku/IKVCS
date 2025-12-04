<template>
  <div class="bili-profile-container">
    <!-- 返回首页按钮 -->
    <div class="bili-back-btn" @click="router.push('/')">
      <el-icon><ArrowLeft /></el-icon>
      <span>返回首页</span>
    </div>

    <!-- 个人中心卡片 -->
    <div class="bili-profile-card">
      <div class="bili-profile-header">
        <h2 class="bili-profile-title">个人中心</h2>
        <p class="bili-profile-subtitle">管理你的个人信息</p>
      </div>

      <div class="bili-profile-content">
        <!-- 头像区域 -->
        <div class="bili-avatar-section">
          <div class="bili-avatar-wrapper" @click="triggerFileInput">
            <el-avatar 
              :src="userStore.avatar" 
              :size="120"
              class="bili-avatar-img"
            />
            <div class="bili-avatar-overlay">
              <el-icon :size="24"><Camera /></el-icon>
              <span>更换头像</span>
            </div>
          </div>
          
          <!-- 隐藏的文件输入 -->
          <input
            ref="fileInputRef"
            type="file"
            accept="image/*"
            style="display: none"
            @change="handleFileSelect"
          />
          
          <el-button 
            type="primary" 
            class="bili-upload-btn"
            @click="triggerFileInput"
          >
            <el-icon><Upload /></el-icon>
            <span>选择图片</span>
          </el-button>
          
          <p class="bili-avatar-tip">支持 JPG、PNG 格式，大小不超过 2MB</p>
        </div>

        <!-- 信息编辑区域 -->
        <div class="bili-info-section">
          <el-form
            ref="formRef"
            :model="formData"
            :rules="rules"
            label-width="100px"
            label-position="left"
            class="bili-form"
          >
            <el-form-item label="用户名">
              <el-input 
                v-model="userInfo.username" 
                disabled 
                class="bili-input-disabled"
              />
              <span class="bili-form-tip">用户名不可修改</span>
            </el-form-item>

            <el-form-item label="昵称" prop="nickname">
              <el-input
                v-model="formData.nickname"
                placeholder="请输入昵称"
                maxlength="50"
                show-word-limit
                class="bili-input"
              />
            </el-form-item>

            <el-form-item label="个人简介" prop="intro">
              <el-input
                v-model="formData.intro"
                type="textarea"
                placeholder="介绍一下自己吧~"
                :rows="4"
                maxlength="500"
                show-word-limit
                class="bili-textarea"
              />
            </el-form-item>

            <el-form-item label="角色">
              <el-tag 
                :type="userInfo.role === 'admin' ? 'danger' : 'info'"
                class="bili-role-tag"
              >
                {{ userInfo.role === 'admin' ? '管理员' : '普通用户' }}
              </el-tag>
            </el-form-item>

            <el-form-item label="注册时间">
              <span class="bili-info-text">{{ formatDate(userInfo.created_at) }}</span>
            </el-form-item>

            <el-form-item label="最后登录">
              <span class="bili-info-text">{{ formatDate(userInfo.last_login_time) }}</span>
            </el-form-item>

            <el-form-item>
              <el-button 
                type="primary" 
                @click="handleSubmit" 
                :loading="submitting"
                class="bili-submit-btn"
              >
                <el-icon v-if="!submitting"><Check /></el-icon>
                <span>{{ submitting ? '保存中...' : '保存修改' }}</span>
              </el-button>
              <el-button 
                @click="handleReset"
                class="bili-reset-btn"
              >
                <el-icon><RefreshLeft /></el-icon>
                <span>重置</span>
              </el-button>
            </el-form-item>
          </el-form>
        </div>
      </div>
    </div>

    <!-- 头像裁剪弹窗 -->
    <AvatarCropper
      v-model="cropperVisible"
      :img-src="selectedImageSrc"
      @confirm="handleCropConfirm"
    />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { 
  ArrowLeft, 
  Camera, 
  Upload, 
  Check, 
  RefreshLeft 
} from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import { updateUserInfo, uploadAvatar } from '@/api/user'
import AvatarCropper from '@/components/AvatarCropper.vue'

const router = useRouter()
const userStore = useUserStore()
const formRef = ref(null)
const fileInputRef = ref(null)
const submitting = ref(false)

// 头像裁剪相关
const cropperVisible = ref(false)
const selectedImageSrc = ref('')

// 用户信息
const userInfo = reactive({
  username: '',
  nickname: '',
  avatar: '',
  intro: '',
  role: '',
  created_at: '',
  last_login_time: ''
})

// 表单数据
const formData = reactive({
  nickname: '',
  intro: ''
})

// 表单验证规则
const rules = {
  nickname: [
    { required: true, message: '请输入昵称', trigger: 'blur' },
    { min: 1, max: 50, message: '昵称长度在 1 到 50 个字符', trigger: 'blur' }
  ],
  intro: [
    { max: 500, message: '简介长度不能超过 500 个字符', trigger: 'blur' }
  ]
}

// 加载用户信息
const loadUserInfo = async () => {
  try {
    await userStore.fetchUserInfo()
    Object.assign(userInfo, userStore.userInfo)
    formData.nickname = userInfo.nickname
    formData.intro = userInfo.intro || ''
  } catch (error) {
    ElMessage.error('加载用户信息失败')
  }
}

// 触发文件选择
const triggerFileInput = () => {
  fileInputRef.value?.click()
}

// 处理文件选择
const handleFileSelect = (event) => {
  const file = event.target.files[0]
  if (!file) return

  // 验证文件类型
  if (!file.type.startsWith('image/')) {
    ElMessage.error('只能上传图片文件!')
    return
  }

  // 验证文件大小（2MB）
  if (file.size > 2 * 1024 * 1024) {
    ElMessage.error('图片大小不能超过 2MB!')
    return
  }

  // 读取图片并显示裁剪器
  const reader = new FileReader()
  reader.onload = (e) => {
    selectedImageSrc.value = e.target.result
    cropperVisible.value = true
  }
  reader.readAsDataURL(file)

  // 清空 input，允许重复选择同一文件
  event.target.value = ''
}

// 处理裁剪确认
const handleCropConfirm = async (file) => {
  try {
    const res = await uploadAvatar(file)
    
    // 刷新用户信息（从服务器获取最新数据）
    await userStore.fetchUserInfo()
    
    // 同步到本地 userInfo
    Object.assign(userInfo, userStore.userInfo)
    
    ElMessage.success('头像上传成功')
  } catch (error) {
    console.error('头像上传失败:', error)
    ElMessage.error(error.response?.data?.detail || '头像上传失败')
  }
}

// 提交表单
const handleSubmit = async () => {
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (!valid) return

    submitting.value = true
    try {
      await updateUserInfo(formData)
      await userStore.fetchUserInfo()
      Object.assign(userInfo, userStore.userInfo)
      ElMessage.success('信息更新成功')
    } catch (error) {
      console.error('信息更新失败:', error)
      ElMessage.error(error.response?.data?.detail || '信息更新失败')
    } finally {
      submitting.value = false
    }
  })
}

// 重置表单
const handleReset = () => {
  formData.nickname = userInfo.nickname
  formData.intro = userInfo.intro || ''
}

// 格���化日期
const formatDate = (dateStr) => {
  if (!dateStr) return '未知'
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN')
}

onMounted(() => {
  loadUserInfo()
})
</script>

<style scoped>
/* 容器 */
.bili-profile-container {
  min-height: 100vh;
  background: var(--bili-bg-2);
  padding: 24px;
}

/* 返回按钮 */
.bili-back-btn {
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
}

.bili-back-btn:hover {
  background: var(--bili-pink);
  color: #fff;
  transform: translateX(-4px);
}

/* 个人中心卡片 */
.bili-profile-card {
  max-width: 1000px;
  margin: 0 auto;
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  overflow: hidden;
  animation: fadeInUp 0.6s ease-out;
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 卡片头部 */
.bili-profile-header {
  padding: 32px 40px;
  background: linear-gradient(135deg, var(--bili-pink) 0%, var(--bili-blue) 100%);
  color: #fff;
}

.bili-profile-title {
  font-size: 28px;
  font-weight: bold;
  margin-bottom: 8px;
}

.bili-profile-subtitle {
  font-size: 14px;
  opacity: 0.9;
}

/* 内容区域 */
.bili-profile-content {
  display: flex;
  gap: 48px;
  padding: 40px;
}

/* 头像区域 */
.bili-avatar-section {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.bili-avatar-wrapper {
  position: relative;
  cursor: pointer;
  border-radius: 50%;
  overflow: hidden;
}

.bili-avatar-img {
  border: 4px solid var(--bili-pink);
  transition: all 0.3s;
}

.bili-avatar-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #fff;
  opacity: 0;
  transition: all 0.3s;
}

.bili-avatar-wrapper:hover .bili-avatar-overlay {
  opacity: 1;
}

.bili-avatar-wrapper:hover .bili-avatar-img {
  transform: scale(1.05);
}

.bili-upload-btn {
  background: var(--bili-pink);
  border: none;
  border-radius: 20px;
  padding: 10px 24px;
}

.bili-upload-btn:hover {
  background: var(--bili-pink-hover);
}

.bili-avatar-tip {
  font-size: 12px;
  color: var(--bili-text-3);
  text-align: center;
  line-height: 1.5;
}

/* 信息编辑区域 */
.bili-info-section {
  flex: 1;
}

.bili-form :deep(.el-form-item__label) {
  font-weight: 600;
  color: var(--bili-text-1);
}

.bili-input :deep(.el-input__wrapper) {
  border-radius: 8px;
  box-shadow: 0 0 0 1px var(--bili-border-1) inset;
  transition: all 0.3s;
}

.bili-input :deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px var(--bili-pink) inset;
}

.bili-input :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 2px var(--bili-pink) inset;
}

.bili-input-disabled :deep(.el-input__wrapper) {
  background: var(--bili-bg-2);
  cursor: not-allowed;
}

.bili-textarea :deep(.el-textarea__inner) {
  border-radius: 8px;
  border: 1px solid var(--bili-border-1);
  transition: all 0.3s;
}

.bili-textarea :deep(.el-textarea__inner:hover) {
  border-color: var(--bili-pink);
}

.bili-textarea :deep(.el-textarea__inner:focus) {
  border-color: var(--bili-pink);
  box-shadow: 0 0 0 2px rgba(251, 114, 153, 0.1);
}

.bili-form-tip {
  font-size: 12px;
  color: var(--bili-text-3);
  margin-left: 8px;
}

.bili-role-tag {
  font-size: 14px;
  padding: 6px 16px;
  border-radius: 12px;
}

.bili-info-text {
  font-size: 14px;
  color: var(--bili-text-2);
}

.bili-submit-btn {
  background: var(--bili-pink);
  border: none;
  border-radius: 20px;
  padding: 10px 32px;
}

.bili-submit-btn:hover {
  background: var(--bili-pink-hover);
}

.bili-reset-btn {
  border: 1px solid var(--bili-border-2);
  border-radius: 20px;
  padding: 10px 32px;
}

.bili-reset-btn:hover {
  border-color: var(--bili-pink);
  color: var(--bili-pink);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .bili-profile-content {
    flex-direction: column;
    align-items: center;
    padding: 24px;
  }
  
  .bili-profile-header {
    padding: 24px;
  }
  
  .bili-profile-title {
    font-size: 24px;
  }
}
</style>
