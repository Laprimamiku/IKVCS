/**
 * 用户操作 Composable
 * 提取用户操作相关的业务逻辑
 */
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { updateUserInfo, uploadAvatar } from '@/api/user'
import type { UpdateUserInfoData } from '@/api/user'

export function useUserActions() {
  const router = useRouter()
  const userStore = useUserStore()

  // 状态
  const submitting = ref(false)

  /**
   * 更新用户信息
   */
  const updateUser = async (data: UpdateUserInfoData) => {
    submitting.value = true
    try {
      await updateUserInfo(data)
      await userStore.fetchUserInfo()
      ElMessage.success('信息更新成功')
      return true
    } catch (error) {
      console.error('信息更新失败:', error)
      const err = error as { response?: { data?: { detail?: string } } }
      ElMessage.error(err.response?.data?.detail || '信息更新失败')
      return false
    } finally {
      submitting.value = false
    }
  }

  /**
   * 上传头像
   */
  const uploadUserAvatar = async (file: File) => {
    try {
      await uploadAvatar(file)
      await userStore.fetchUserInfo()
      ElMessage.success('头像上传成功')
      return true
    } catch (error) {
      console.error('头像上传失败:', error)
      const err = error as { response?: { data?: { detail?: string } } }
      ElMessage.error(err.response?.data?.detail || '头像上传失败')
      return false
    }
  }

  /**
   * 退出登录
   */
  const logout = async () => {
    try {
      await userStore.logout()
      router.push('/')
      ElMessage.success('已退出登录')
    } catch (error) {
      console.error('退出登录失败:', error)
      ElMessage.error('退出登录失败')
    }
  }

  return {
    // 状态
    submitting,
    
    // 方法
    updateUser,
    uploadUserAvatar,
    logout,
  }
}

