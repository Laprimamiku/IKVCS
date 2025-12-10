<template>
  <div class="profile-container">
    <!-- 个人中心卡片 -->
    <div class="profile-card">
      <ProfileHeader @back="router.push('/')" />

      <div class="profile-content">
        <!-- 头像区域 -->
        <AvatarSection
          :avatar="userStore.avatar"
          @file-selected="handleFileSelect"
        />

        <!-- 信息编辑区域 -->
        <InfoForm
          ref="infoFormRef"
          :user-info="userInfo"
          :submitting="submitting"
          @submit="handleSubmit"
          @reset="handleReset"
        />
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

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { useUserActions } from '@/composables/useUserActions'
import ProfileHeader from '@/components/profile/ProfileHeader.vue'
import AvatarSection from '@/components/profile/AvatarSection.vue'
import InfoForm from '@/components/profile/InfoForm.vue'
import AvatarCropper from '@/components/AvatarCropper.vue'
import type { UserInfo } from '@/types/entity'

const router = useRouter()
const userStore = useUserStore()
const { submitting, updateUser, uploadUserAvatar } = useUserActions()
const infoFormRef = ref<InstanceType<typeof InfoForm> | null>(null)

// 头像裁剪相关
const cropperVisible = ref(false)
const selectedImageSrc = ref('')

// 用户信息
const userInfo = reactive<UserInfo>({
  id: 0,
  username: '',
  nickname: '',
  avatar: '',
  intro: '',
  role: '',
  created_at: '',
  last_login_time: ''
})

// 加载用户信息
const loadUserInfo = async () => {
  try {
    await userStore.fetchUserInfo()
    Object.assign(userInfo, userStore.userInfo)
    // 同步表单数据
    if (infoFormRef.value) {
      infoFormRef.value.setFormData({
        nickname: userInfo.nickname,
        intro: userInfo.intro || ''
      })
    }
  } catch (error) {
    ElMessage.error('加载用户信息失败')
  }
}

// 处理文件选择
const handleFileSelect = (file: File) => {
  // 读取图片并显示裁剪器
  const reader = new FileReader()
  reader.onload = (e) => {
    selectedImageSrc.value = e.target?.result as string
    cropperVisible.value = true
  }
  reader.readAsDataURL(file)
}

// 处理裁剪确认
const handleCropConfirm = async (file: File) => {
  const success = await uploadUserAvatar(file)
  if (success) {
    // 同步到本地 userInfo
    Object.assign(userInfo, userStore.userInfo)
  }
}

// 提交表单
const handleSubmit = async (data: { nickname: string; intro: string }) => {
  const success = await updateUser(data)
  if (success) {
    // 同步到本地 userInfo
    Object.assign(userInfo, userStore.userInfo)
  }
}

// 重置表单
const handleReset = () => {
  if (infoFormRef.value) {
    infoFormRef.value.setFormData({
      nickname: userInfo.nickname,
      intro: userInfo.intro || ''
    })
  }
}

onMounted(() => {
  loadUserInfo()
})
</script>

<style lang="scss" scoped>
.profile-container {
  min-height: 100vh;
  background: var(--bili-bg-2);
  padding: 24px;
}

.profile-card {
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

.profile-content {
  display: flex;
  gap: 48px;
  padding: 40px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .profile-content {
    flex-direction: column;
    align-items: center;
    padding: 24px;
  }
}
</style>
