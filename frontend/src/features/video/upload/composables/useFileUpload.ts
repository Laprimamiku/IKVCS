/**
 * 文件上传 Composable
 * 
 * 职责：文件选择、验证、预览
 */
import { ref, type Ref } from 'vue'
import { ElMessage } from 'element-plus'

export interface FileUploadState {
  videoFile: Ref<File | null>
  coverFile: Ref<File | null>
  subtitleFile: Ref<File | null>
  videoPreviewUrl: Ref<string>
  coverPreviewUrl: Ref<string>
}

const MAX_VIDEO_SIZE = 2 * 1024 * 1024 * 1024 // 2GB
const MAX_COVER_SIZE = 5 * 1024 * 1024 // 5MB

export function useFileUpload() {
  const videoFile = ref<File | null>(null)
  const coverFile = ref<File | null>(null)
  const subtitleFile = ref<File | null>(null)
  const videoPreviewUrl = ref<string>('')
  const coverPreviewUrl = ref<string>('')

  // 验证视频文件
  const validateVideoFile = (file: File): boolean => {
    if (file.size > MAX_VIDEO_SIZE) {
      ElMessage.error('视频文件大小不能超过 2GB')
      return false
    }
    return true
  }

  // 验证封面文件
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

  // 验证字幕文件
  const validateSubtitleFile = (file: File): boolean => {
    const validExts = ['.srt', '.vtt', '.json', '.ass']
    const ext = '.' + file.name.split('.').pop()?.toLowerCase()
    if (!ext || !validExts.includes(ext)) {
      ElMessage.warning('字幕格式不支持，仅支持 SRT、VTT、JSON、ASS')
      return false
    }
    return true
  }

  // 选择视频文件
  const selectVideoFile = (file: File): boolean => {
    if (!validateVideoFile(file)) {
      return false
    }
    videoFile.value = file
    videoPreviewUrl.value = URL.createObjectURL(file)
    return true
  }

  // 选择封面文件
  const selectCoverFile = (file: File): boolean => {
    if (!validateCoverFile(file)) {
      return false
    }
    coverFile.value = file
    coverPreviewUrl.value = URL.createObjectURL(file)
    return true
  }

  // 选择字幕文件
  const selectSubtitleFile = (file: File): boolean => {
    if (!validateSubtitleFile(file)) {
      return false
    }
    subtitleFile.value = file
    return true
  }

  // 移除视频文件
  const removeVideoFile = () => {
    if (videoPreviewUrl.value) {
      URL.revokeObjectURL(videoPreviewUrl.value)
    }
    videoFile.value = null
    videoPreviewUrl.value = ''
  }

  // 移除封面文件
  const removeCoverFile = () => {
    if (coverPreviewUrl.value) {
      URL.revokeObjectURL(coverPreviewUrl.value)
    }
    coverFile.value = null
    coverPreviewUrl.value = ''
  }

  // 移除字幕文件
  const removeSubtitleFile = () => {
    subtitleFile.value = null
  }

  // 重置所有文件
  const resetFiles = () => {
    removeVideoFile()
    removeCoverFile()
    removeSubtitleFile()
  }

  // 格式化文件大小
  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return (bytes / Math.pow(k, i)).toFixed(2) + ' ' + sizes[i]
  }

  return {
    // 状态
    videoFile,
    coverFile,
    subtitleFile,
    videoPreviewUrl,
    coverPreviewUrl,
    // 方法
    selectVideoFile,
    selectCoverFile,
    selectSubtitleFile,
    removeVideoFile,
    removeCoverFile,
    removeSubtitleFile,
    resetFiles,
    formatFileSize,
  }
}

