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
} from "@/features/video/upload/api/upload.api"
import { uploadVideoCover, uploadVideoSubtitle } from "@/features/video/shared/api/video.api"
import { uploadRequest } from "@/shared/utils/request"

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

  // 封面和字幕上传进度
  const coverUploadProgress = ref<number>(0)
  const subtitleUploadProgress = ref<number>(0)
  const coverUploading = ref<boolean>(false)
  const subtitleUploading = ref<boolean>(false)

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
      // 使用后端返回的 total_chunks（如果可用），否则使用计算值
      if (initData.total_chunks && initData.total_chunks > 0) {
        totalChunks.value = initData.total_chunks
      } else {
        totalChunks.value = chunks
      }
      uploadedChunks.value = totalChunks.value
      uploadComplete.value = true
      uploading.value = false
      ElMessage.success('视频秒传成功！')
      return initData
    }

    // 如果后端返回了 total_chunks，使用后端的值（更可靠）
    if (initData.total_chunks && initData.total_chunks > 0) {
      if (initData.total_chunks !== chunks) {
        console.warn(
          `总分片数不一致：前端计算=${chunks}，后端返回=${initData.total_chunks}，使用后端值`
        )
      }
      totalChunks.value = initData.total_chunks
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

    // 验证 totalChunks 是否有效
    if (totalChunks.value <= 0) {
      throw new Error('总分片数无效，请重新初始化上传')
    }

    // 计算期望的总分片数（从文件大小）
    const calculatedChunks = Math.ceil(file.size / CHUNK_SIZE)
    
    // 如果计算值和当前值不一致，记录警告但不强制修改
    // 因为后端可能已经保存了正确的 total_chunks，我们应该信任后端
    if (calculatedChunks !== totalChunks.value) {
      console.warn(
        `总分片数不一致：前端计算值=${calculatedChunks}，当前值=${totalChunks.value}。` +
        `将使用当前值 ${totalChunks.value}（后端可能已保存正确的值）`
      )
    }

    // 确保 uploadedList 中的索引都有效
    const validUploadedList = uploadedList.filter(idx => idx >= 0 && idx < totalChunks.value)
    if (validUploadedList.length !== uploadedList.length) {
      console.warn(
        `发现无效的已上传分片索引：原始列表=${uploadedList.join(',')}，` +
        `有效列表=${validUploadedList.join(',')}，总分片数=${totalChunks.value}`
      )
    }

    console.log(
      `开始上传分片：hash=${hash}, totalChunks=${totalChunks.value}, ` +
      `uploadedList=[${validUploadedList.join(',')}], 需要上传=${totalChunks.value - validUploadedList.length}个`
    )

    for (let i = 0; i < totalChunks.value; i++) {
      // 验证分片索引有效性（双重检查）
      if (i < 0 || i >= totalChunks.value) {
        console.error(`无效的分片索引: ${i}，总分片数: ${totalChunks.value}`)
        throw new Error(`无效的分片索引: ${i}`)
      }

      // 跳过已上传的分片
      if (validUploadedList.includes(i)) {
        console.log(`跳过已上传的分片: ${i}`)
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

      console.log(`准备上传分片 ${i}：start=${start}, end=${end}, size=${chunk.size}`)

      try {
        await uploadChunk(hash, i, chunk)
        uploadedChunks.value++
        uploadedBytes.value += chunk.size
        console.log(`分片 ${i} 上传成功`)
      } catch (error: unknown) {
        console.error(`分片 ${i} 上传失败:`, error)
        // 如果错误是分片索引无效，提供更详细的错误信息
        const errorDetail = error?.response?.data?.detail || error?.message || String(error)
        if (errorDetail.includes('分片索引') || errorDetail.includes('无效')) {
          throw new Error(
            `分片索引 ${i} 无效（总分片数：${totalChunks.value}）。` +
            `错误详情：${errorDetail}。请刷新页面后重试。`
          )
        }
        throw new Error(`分片 ${i} 上传失败: ${errorDetail}`)
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

      // 更新上传详情显示
      const updateUploadDetail = () => {
        const parts: string[] = []
        if (coverFile) {
          parts.push(`封面: ${coverUploadProgress.value}%`)
        }
        if (subtitleFile) {
          parts.push(`字幕: ${subtitleUploadProgress.value}%`)
        }
        if (parts.length > 0) {
          uploadDetail.value = parts.join(' | ')
        } else {
          uploadDetail.value = '并行上传中，请勿关闭窗口'
        }
      }

      // 并行上传封面和字幕（如果有）
      const uploadTasks: Promise<any>[] = []
      
      if (coverFile) {
        coverUploading.value = true
        coverUploadProgress.value = 0
        uploadStatus.value = '正在上传封面和字幕...'
        uploadDetail.value = '并行上传中，请勿关闭窗口'
        uploadTasks.push(
          uploadVideoCoverWithProgress(videoId, coverFile, (progress) => {
            coverUploadProgress.value = progress
            updateUploadDetail()
          }).catch((error) => {
            console.error('封面上传失败:', error)
            ElMessage.warning('封面上传失败，可稍后重新上传')
            coverUploading.value = false
            // 不抛出错误，允许继续
            return null
          }).finally(() => {
            coverUploading.value = false
          })
        )
      }

      if (subtitleFile) {
        subtitleUploading.value = true
        subtitleUploadProgress.value = 0
        if (!coverFile) {
          uploadStatus.value = '正在上传字幕...'
          uploadDetail.value = '支持 SRT、VTT、JSON、ASS'
        } else {
          uploadStatus.value = '正在上传封面和字幕...'
        }
        uploadTasks.push(
          uploadVideoSubtitleWithProgress(videoId, subtitleFile, (progress) => {
            subtitleUploadProgress.value = progress
            updateUploadDetail()
          }).catch((error) => {
            console.error('字幕上传失败:', error)
            ElMessage.warning('字幕上传失败，可稍后重新上传')
            subtitleUploading.value = false
            // 不抛出错误，允许继续
            return null
          }).finally(() => {
            subtitleUploading.value = false
          })
        )
      }

      // 等待所有上传任务完成
      if (uploadTasks.length > 0) {
        await Promise.all(uploadTasks)
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
      // 重新计算总分片数（确保正确）
      const chunks = Math.ceil(file.size / CHUNK_SIZE)
      totalChunks.value = chunks

      // 获取已上传分片
      const progressRes = await getUploadProgress(fileHash.value)
      
      // 处理响应：request 拦截器返回 { success: true, data: {...} }
      let progressData: { uploaded_chunks: number[], total_chunks?: number }
      if ((progressRes as any)?.success && (progressRes as any)?.data) {
        progressData = (progressRes as any).data as { uploaded_chunks: number[], total_chunks?: number }
      } else {
        progressData = (progressRes as unknown) as { uploaded_chunks: number[], total_chunks?: number }
      }

      // 如果后端返回了 total_chunks，使用后端的值（更可靠）
      if (progressData.total_chunks && progressData.total_chunks > 0) {
        totalChunks.value = progressData.total_chunks
      }

      const uploadedList = progressData.uploaded_chunks || []
      uploadedChunks.value = uploadedList.length
      uploadedBytes.value = uploadedChunks.value * CHUNK_SIZE

      // 验证：确保 uploadedList 中的所有索引都小于 totalChunks
      const invalidChunks = uploadedList.filter(idx => idx < 0 || idx >= totalChunks.value)
      if (invalidChunks.length > 0) {
        console.warn(`发现无效的分片索引: ${invalidChunks.join(', ')}，将忽略`)
        // 过滤掉无效的分片索引
        const validList = uploadedList.filter(idx => idx >= 0 && idx < totalChunks.value)
        uploadedList.length = 0
        uploadedList.push(...validList)
        uploadedChunks.value = uploadedList.length
      }

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

  // 带进度回调的封面上传函数
  const uploadVideoCoverWithProgress = async (
    videoId: number,
    file: File,
    onProgress: (progress: number) => void
  ): Promise<any> => {
    const formData = new FormData()
    formData.append('cover', file)
    
    return uploadRequest.post(`/videos/${videoId}/cover`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (progressEvent) => {
        if (progressEvent.total) {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total)
          onProgress(progress)
        }
      }
    })
  }

  // 带进度回调的字幕上传函数
  const uploadVideoSubtitleWithProgress = async (
    videoId: number,
    file: File,
    onProgress: (progress: number) => void
  ): Promise<any> => {
    const formData = new FormData()
    formData.append('subtitle', file)
    
    return uploadRequest.post(`/videos/${videoId}/subtitle`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (progressEvent) => {
        if (progressEvent.total) {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total)
          onProgress(progress)
        }
      }
    })
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
    coverUploadProgress.value = 0
    subtitleUploadProgress.value = 0
    coverUploading.value = false
    subtitleUploading.value = false
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
    // 封面和字幕上传进度
    coverUploadProgress,
    subtitleUploadProgress,
    coverUploading,
    subtitleUploading,
    // 方法
    startUpload,
    pauseUpload,
    resumeUpload,
    resetUpload,
  }
}

