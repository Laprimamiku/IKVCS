/**
 * 分片上传 Composable
 * 
 * 职责：文件哈希计算、分片上传、断点续传、进度管理
 */
import { ref, computed, type Ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  initUpload,
  uploadChunk,
  finishUpload,
  getUploadProgress,
  type InitUploadResponse,
  type FinishUploadResponse,
} from '@/api/upload'
import { uploadVideoCover, uploadVideoSubtitle } from '@/api/video'

export interface ChunkUploadState {
  uploading: Ref<boolean>
  uploadComplete: Ref<boolean>
  uploadStatus: Ref<string>
  uploadDetail: Ref<string>
  fileHash: Ref<string>
  totalChunks: Ref<number>
  uploadedChunks: Ref<number>
  uploadedBytes: Ref<number>
  uploadStartTime: Ref<number>
  totalProgress: Ref<number>
  uploadSpeed: Ref<string>
  remainingTime: Ref<string>
}

const CHUNK_SIZE = 5 * 1024 * 1024 // 5MB

export function useChunkUpload() {
  const uploading = ref<boolean>(false)
  const uploadComplete = ref<boolean>(false)
  const uploadStatus = ref<string>('准备上传...')
  const uploadDetail = ref<string>('')
  const fileHash = ref<string>('')
  const totalChunks = ref<number>(0)
  const uploadedChunks = ref<number>(0)
  const uploadedBytes = ref<number>(0)
  const uploadStartTime = ref<number>(0)

  // 计算总进度
  const totalProgress = computed(() => {
    if (totalChunks.value === 0) return 0
    return Math.floor((uploadedChunks.value / totalChunks.value) * 100)
  })

  // 计算上传速度
  const uploadSpeed = computed(() => {
    if (uploadStartTime.value === 0) return '0 KB/s'
    const elapsed = (Date.now() - uploadStartTime.value) / 1000
    if (elapsed === 0) return '0 KB/s'
    const speed = uploadedBytes.value / elapsed
    return formatSpeed(speed)
  })

  // 计算剩余时间
  const remainingTime = computed(() => {
    if (uploadStartTime.value === 0 || uploadedBytes.value === 0) {
      return '计算中...'
    }
    const elapsed = (Date.now() - uploadStartTime.value) / 1000
    const speed = uploadedBytes.value / elapsed
    if (speed === 0) return '计算中...'
    const fileSize = totalChunks.value * CHUNK_SIZE
    const remaining = (fileSize - uploadedBytes.value) / speed
    return formatTime(remaining)
  })

  // 计算文件哈希（SHA-256）
  const calculateFileHash = async (file: File): Promise<string> => {
    uploadStatus.value = '正在计算文件哈希...'
    uploadDetail.value = '用于秒传检测和断点续传'

    try {
      const buffer = await file.arrayBuffer()
      const hashBuffer = await crypto.subtle.digest('SHA-256', buffer)
      const hashArray = Array.from(new Uint8Array(hashBuffer))
      const hashHex = hashArray
        .map((b) => b.toString(16).padStart(2, '0'))
        .join('')
      return hashHex
    } catch (error) {
      console.error('计算文件哈希失败:', error)
      throw new Error('计算文件哈希失败')
    }
  }

  // 初始化上传
  const initializeUpload = async (
    file: File,
    hash: string
  ): Promise<InitUploadResponse> => {
    uploadStatus.value = '初始化上传...'
    uploadDetail.value = '检查是否可以秒传'

    const chunks = Math.ceil(file.size / CHUNK_SIZE)
    totalChunks.value = chunks

    const response = await initUpload({
      file_hash: hash,
      file_name: file.name,
      total_chunks: chunks,
      file_size: file.size,
    })

    // 处理响应：request 拦截器返回 { success: true, data: {...} }
    let initData: InitUploadResponse
    if ((response as any)?.success && (response as any)?.data) {
      initData = (response as any).data as InitUploadResponse
    } else {
      initData = (response as unknown) as InitUploadResponse
    }

    // 检查是否秒传
    if (initData.is_completed && initData.video_id) {
      uploadStatus.value = '秒传成功！'
      uploadDetail.value = '文件已存在，无需重新上传'
      uploadedChunks.value = chunks
      uploadComplete.value = true
      uploading.value = false
      ElMessage.success('视频秒传成功！')
      return initData
    }

    // 获取已上传分片
    const uploadedList = initData.uploaded_chunks || []
    uploadedChunks.value = uploadedList.length
    uploadedBytes.value = uploadedChunks.value * CHUNK_SIZE

    return initData
  }

  // 上传分片
  const uploadChunks = async (
    file: File,
    hash: string,
    uploadedList: number[]
  ): Promise<void> => {
    uploadStatus.value = '正在上传视频...'

    for (let i = 0; i < totalChunks.value; i++) {
      // 跳过已上传的分片
      if (uploadedList.includes(i)) {
        continue
      }

      // 检查是否暂停
      if (!uploading.value) {
        throw new Error('上传已暂停')
      }

      const start = i * CHUNK_SIZE
      const end = Math.min(start + CHUNK_SIZE, file.size)
      const chunk = file.slice(start, end)

      uploadDetail.value = `正在上传第 ${i + 1} / ${totalChunks.value} 个分片`

      try {
        await uploadChunk(hash, i, chunk)
        uploadedChunks.value++
        uploadedBytes.value += chunk.size
      } catch (error) {
        console.error(`分片 ${i} 上传失败:`, error)
        throw new Error(`分片 ${i} 上传失败`)
      }
    }
  }

  // 完成上传
  const completeUpload = async (
    videoInfo: {
      title: string
      description: string
      category_id: number
    },
    coverFile: File | null,
    subtitleFile: File | null
  ): Promise<number> => {
    uploadStatus.value = '正在完成上传...'
    uploadDetail.value = '合并分片并创建视频记录'

    try {
      const res = await finishUpload({
        file_hash: fileHash.value,
        title: videoInfo.title,
        description: videoInfo.description,
        category_id: videoInfo.category_id,
        cover_url: '',
      })

      // 处理响应：request 拦截器返回 { success: true, data: { video_id } }
      let videoId: number | undefined
      if ((res as any)?.success && (res as any)?.data) {
        const data = (res as any).data as FinishUploadResponse
        videoId = data.video_id
      } else {
        const data = (res as unknown) as FinishUploadResponse
        videoId = data.video_id
      }

      if (!videoId) {
        console.error('finishUpload 响应:', res)
        throw new Error('未获取到视频ID，请稍后重试')
      }

      // 上传封面（如果有）
      if (coverFile) {
        uploadStatus.value = '正在上传封面...'
        uploadDetail.value = '请勿关闭窗口'
        await uploadVideoCover(videoId, coverFile)
      }

      // 上传字幕（如果有）
      if (subtitleFile) {
        uploadStatus.value = '正在上传字幕...'
        uploadDetail.value = '支持 SRT、VTT、JSON、ASS'
        await uploadVideoSubtitle(videoId, subtitleFile)
      }

      uploadStatus.value = '上传完成！'
      uploadDetail.value = '视频正在转码中，稍后即可观看'
      uploadComplete.value = true
      uploading.value = false

      ElMessage.success('视频上传成功！')
      return videoId
    } catch (error) {
      console.error('完成上传失败:', error)
      throw error
    }
  }

  // 开始上传
  const startUpload = async (
    file: File,
    videoInfo: {
      title: string
      description: string
      category_id: number
    },
    coverFile: File | null,
    subtitleFile: File | null
  ): Promise<number> => {
    if (uploading.value) {
      ElMessage.warning('正在上传，请勿重复提交')
      throw new Error('正在上传，请勿重复提交')
    }
    uploading.value = true
    uploadStartTime.value = Date.now()

    try {
      // 1. 计算文件哈希
      const hash = await calculateFileHash(file)
      fileHash.value = hash

      // 2. 初始化上传
      const initRes = await initializeUpload(file, hash)

      // 如果秒传成功，直接返回视频ID
      if (initRes.is_completed && initRes.video_id) {
        return initRes.video_id
      }

      // 3. 上传分片
      const uploadedList = initRes.uploaded_chunks || []
      await uploadChunks(file, hash, uploadedList)

      // 4. 完成上传
      const videoId = await completeUpload(videoInfo, coverFile, subtitleFile)
      return videoId
    } catch (error: any) {
      console.error('上传失败:', error)
      ElMessage.error(error.message || '上传失败')
      uploading.value = false
      uploadStatus.value = '上传失败'
      uploadDetail.value = error.message || '请重试'
      throw error
    }
  }

  // 暂停上传
  const pauseUpload = () => {
    uploading.value = false
    uploadStatus.value = '上传已暂停'
    uploadDetail.value = '点击"继续上传"可恢复'
  }

  // 继续上传
  const resumeUpload = async (
    file: File,
    videoInfo: {
      title: string
      description: string
      category_id: number
    },
    coverFile: File | null,
    subtitleFile: File | null
  ): Promise<number> => {
    if (uploading.value) {
      ElMessage.warning('正在上传，请勿重复提交')
      throw new Error('正在上传，请勿重复提交')
    }
    uploading.value = true
    uploadStartTime.value = Date.now()

    try {
      // 获取已上传分片
      const progressRes = await getUploadProgress(fileHash.value)
      
      // 处理响应：request 拦截器返回 { success: true, data: {...} }
      let progressData: { uploaded_chunks: number[] }
      if ((progressRes as any)?.success && (progressRes as any)?.data) {
        progressData = (progressRes as any).data as { uploaded_chunks: number[] }
      } else {
        progressData = (progressRes as unknown) as { uploaded_chunks: number[] }
      }

      const uploadedList = progressData.uploaded_chunks || []
      uploadedChunks.value = uploadedList.length
      uploadedBytes.value = uploadedChunks.value * CHUNK_SIZE

      // 继续上传
      await uploadChunks(file, fileHash.value, uploadedList)
      const videoId = await completeUpload(videoInfo, coverFile, subtitleFile)
      return videoId
    } catch (error: any) {
      console.error('继续上传失败:', error)
      ElMessage.error('继续上传失败')
      uploading.value = false
      throw error
    }
  }

  // 重置上传状态
  const resetUpload = () => {
    uploading.value = false
    uploadComplete.value = false
    uploadStatus.value = '准备上传...'
    uploadDetail.value = ''
    fileHash.value = ''
    totalChunks.value = 0
    uploadedChunks.value = 0
    uploadedBytes.value = 0
    uploadStartTime.value = 0
  }

  // 工具函数
  const formatSpeed = (bytesPerSecond: number): string => {
    if (bytesPerSecond === 0) return '0 KB/s'
    const k = 1024
    const sizes = ['B/s', 'KB/s', 'MB/s']
    const i = Math.floor(Math.log(bytesPerSecond) / Math.log(k))
    return (bytesPerSecond / Math.pow(k, i)).toFixed(2) + ' ' + sizes[i]
  }

  const formatTime = (seconds: number): string => {
    if (seconds < 60) return `${Math.floor(seconds)} 秒`
    if (seconds < 3600) return `${Math.floor(seconds / 60)} 分钟`
    return `${Math.floor(seconds / 3600)} 小时`
  }

  return {
    // 状态
    uploading,
    uploadComplete,
    uploadStatus,
    uploadDetail,
    fileHash,
    totalChunks,
    uploadedChunks,
    uploadedBytes,
    uploadStartTime,
    totalProgress,
    uploadSpeed,
    remainingTime,
    // 方法
    startUpload,
    pauseUpload,
    resumeUpload,
    resetUpload,
  }
}

