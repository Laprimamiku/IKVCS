<template>
  <div class="file-selector">
    <!-- 视频上传区 -->
    <div class="upload-section">
      <div class="file-upload-box" @click="triggerVideoSelect">
        <input
          ref="videoInputRef"
          type="file"
          accept="video/*"
          style="display: none"
          @change="handleVideoChange"
        />
        <div v-if="!videoFile" class="upload-placeholder">
          <el-icon :size="60" color="#409EFF"><Upload /></el-icon>
          <p class="upload-text">点击选择视频文件</p>
          <p class="upload-hint">支持 MP4、AVI、MOV 等格式，最大 2GB</p>
        </div>
        <div v-else class="file-preview">
          <video
            v-if="videoPreviewUrl"
            :src="videoPreviewUrl"
            controls
            class="video-preview"
          />
          <div class="file-info">
            <p class="file-name">{{ videoFile.name }}</p>
            <p class="file-size">{{ formatFileSize(videoFile?.size || 0) }}</p>
            <el-button type="danger" size="small" @click.stop="handleRemoveVideo">
              重新选择
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- 封面上传区 -->
    <div class="upload-section">
      <h3>视频封面</h3>
      <div class="cover-upload-box" @click="triggerCoverSelect">
        <input
          ref="coverInputRef"
          type="file"
          accept="image/*"
          style="display: none"
          @change="handleCoverChange"
        />
        <div v-if="!coverFile" class="upload-placeholder small">
          <el-icon :size="40" color="#409EFF"><Picture /></el-icon>
          <p class="upload-text">选择封面图片</p>
        </div>
        <div v-else class="cover-preview">
          <img :src="coverPreviewUrl" alt="封面预览" />
          <el-button
            type="danger"
            size="small"
            circle
            class="remove-btn"
            @click.stop="handleRemoveCover"
          >
            <el-icon><Close /></el-icon>
          </el-button>
        </div>
      </div>
    </div>

    <!-- 字幕上传区 -->
    <div class="upload-section">
      <h3>字幕文件（可选）</h3>
      <el-upload
        ref="subtitleUploadRef"
        :auto-upload="false"
        :limit="1"
        accept=".srt,.vtt,.json,.ass"
        :on-change="handleSubtitleChange"
        :on-remove="handleRemoveSubtitle"
      >
        <el-button type="primary" plain>
          <el-icon><Document /></el-icon>
          选择字幕文件
        </el-button>
        <template #tip>
          <div class="el-upload__tip">支持 SRT、VTT、JSON、ASS 格式</div>
        </template>
      </el-upload>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Upload, Picture, Document, Close } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import type { UploadFile } from 'element-plus'
import { formatFileSize } from "@/shared/utils/formatters"

const props = defineProps<{
  videoFile: File | null
  coverFile: File | null
  subtitleFile: File | null
  videoPreviewUrl: string
  coverPreviewUrl: string
}>()

const emit = defineEmits<{
  'video-selected': [file: File]
  'cover-selected': [file: File]
  'subtitle-selected': [file: File]
  'video-removed': []
  'cover-removed': []
  'subtitle-removed': []
}>()

const videoInputRef = ref<HTMLInputElement | null>(null)
const coverInputRef = ref<HTMLInputElement | null>(null)
const subtitleUploadRef = ref<any>(null)

const MAX_VIDEO_SIZE = 2 * 1024 * 1024 * 1024 // 2GB
const MAX_COVER_SIZE = 5 * 1024 * 1024 // 5MB

// 使用工具函数格式化文件大小

const triggerVideoSelect = () => {
  videoInputRef.value?.click()
}

const triggerCoverSelect = () => {
  coverInputRef.value?.click()
}

const validateVideoFile = (file: File): boolean => {
  if (file.size > MAX_VIDEO_SIZE) {
    ElMessage.error('视频文件大小不能超过 2GB')
    return false
  }
  return true
}

const validateCoverFile = (file: File): boolean => {
  const validTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp']
  if (!validTypes.includes(file.type)) {
    ElMessage.warning('封面格式不支持，仅支持 JPG、PNG、WEBP')
    return false
  }
  if (file.size > MAX_COVER_SIZE) {
    ElMessage.warning('封面文件过大，最大 5MB')
    return false
  }
  return true
}

const validateSubtitleFile = (file: File): boolean => {
  const validExts = ['.srt', '.vtt', '.json', '.ass']
  const ext = '.' + file.name.split('.').pop()?.toLowerCase()
  if (!ext || !validExts.includes(ext)) {
    ElMessage.warning('字幕格式不支持，仅支持 SRT、VTT、JSON、ASS')
    return false
  }
  return true
}

const handleVideoChange = (event: Event) => {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return

  if (validateVideoFile(file)) {
    emit('video-selected', file)
  }
}

const handleCoverChange = (event: Event) => {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return

  if (validateCoverFile(file)) {
    emit('cover-selected', file)
  }
}

const handleSubtitleChange = (file: UploadFile) => {
  if (!file.raw) return

  if (validateSubtitleFile(file.raw)) {
    emit('subtitle-selected', file.raw)
  }
}

const handleRemoveVideo = () => {
  if (videoInputRef.value) {
    videoInputRef.value.value = ''
  }
  emit('video-removed')
}

const handleRemoveCover = () => {
  if (coverInputRef.value) {
    coverInputRef.value.value = ''
  }
  emit('cover-removed')
}

const handleRemoveSubtitle = () => {
  emit('subtitle-removed')
}
</script>

<style lang="scss" scoped>
.file-selector {
  display: flex;
  flex-direction: column;
  gap: 32px; // 增加间距，从 var(--spacing-xl) 改为固定值 32px
}

.upload-section {
  h3 {
    font-size: 18px;
    margin-bottom: 16px;
    color: var(--text-primary);
    font-weight: 500;
  }
}

.file-upload-box {
  border: 2px dashed var(--border-base);
  border-radius: 12px;
  padding: 48px 32px; // 增加内边距，从 var(--spacing-2xl) 改为更大的值
  cursor: pointer;
  transition: all 0.3s ease;
  background: #fafafa;

  &:hover {
    border-color: var(--primary-color);
    background: #f0f7ff;
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  }
}

.upload-placeholder {
  text-align: center;
  padding: 32px 0; // 增加内边距

  &.small {
    padding: 24px 0; // 增加小尺寸的内边距
  }
}

.upload-text {
  font-size: 16px;
  color: var(--text-primary);
  margin: 16px 0 8px; // 增加间距
  font-weight: 500;
}

.upload-hint {
  font-size: 14px;
  color: var(--text-secondary);
  margin-top: 8px;
}

.file-preview {
  display: flex;
  flex-direction: column;
  gap: 20px; // 增加间距
}

.video-preview {
  width: 100%;
  max-height: 400px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.file-info {
  text-align: center;
  padding: 16px 0; // 增加内边距
}

.file-name {
  font-size: 15px;
  color: var(--text-primary);
  margin-bottom: 8px;
  font-weight: 500;
  word-break: break-all;
}

.file-size {
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 16px; // 增加间距
}

.cover-upload-box {
  width: 320px; // 稍微增加宽度
  height: 180px; // 调整高度比例
  border: 2px dashed var(--border-base);
  border-radius: 8px;
  cursor: pointer;
  overflow: hidden;
  position: relative;
  transition: all 0.3s ease;
  background: #fafafa;

  &:hover {
    border-color: var(--primary-color);
    background: #f0f7ff;
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  }
}

.cover-preview {
  width: 100%;
  height: 100%;
  position: relative;

  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
}

.remove-btn {
  position: absolute;
  top: var(--spacing-sm);
  right: var(--spacing-sm);
}

@media (max-width: 768px) {
  .cover-upload-box {
    width: 100%;
  }
}
</style>
