<template>
  <div class="avatar-section">
    <div class="avatar-wrapper" @click="triggerFileInput">
      <el-avatar 
        :src="avatar" 
        :size="120"
        class="avatar-img"
      />
      <div class="avatar-overlay">
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
      class="upload-btn"
      @click="triggerFileInput"
    >
      <el-icon><Upload /></el-icon>
      <span>选择图片</span>
    </el-button>
    
    <p class="avatar-tip">支持 JPG、PNG 格式，大小不超过 2MB</p>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Camera, Upload } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

defineProps<{
  avatar?: string
}>()

const emit = defineEmits<{
  fileSelected: [file: File]
}>()

const fileInputRef = ref<HTMLInputElement | null>(null)

const triggerFileInput = () => {
  fileInputRef.value?.click()
}

const handleFileSelect = (event: Event) => {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
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

  emit('fileSelected', file)

  // 清空 input，允许重复选择同一文件
  target.value = ''
}
</script>

<style lang="scss" scoped>
.avatar-section {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.avatar-wrapper {
  position: relative;
  cursor: pointer;
  border-radius: 50%;
  overflow: hidden;
}

.avatar-img {
  border: 4px solid var(--bili-pink);
  transition: all 0.3s;
}

.avatar-overlay {
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

.avatar-wrapper:hover .avatar-overlay {
  opacity: 1;
}

.avatar-wrapper:hover .avatar-img {
  transform: scale(1.05);
}

.upload-btn {
  background: var(--bili-pink);
  border: none;
  border-radius: 20px;
  padding: 10px 24px;

  &:hover {
    background: var(--bili-pink-hover);
  }
}

.avatar-tip {
  font-size: 12px;
  color: var(--bili-text-3);
  text-align: center;
  line-height: 1.5;
  margin: 0;
}
</style>

