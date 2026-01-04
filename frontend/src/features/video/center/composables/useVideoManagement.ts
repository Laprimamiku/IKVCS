/**
 * 视频管理 Composable
 * 提取视频管理相关的业务逻辑
 */
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { usePagination } from '@/shared/composables/usePagination'
import { 
  getMyVideos, 
  updateVideo, 
  deleteVideo, 
  uploadVideoCover, 
  uploadVideoSubtitle,
  generateVideoOutline
} from "@/features/video/shared/api/video.api"
import { getCategories } from "@/features/video/shared/api/category.api"
import type { Video, Category, PageResult, VideoUpdateData } from "@/shared/types/entity"

export function useVideoManagement() {
  const router = useRouter()

  // 使用通用分页 Composable
  const pagination = usePagination({
    initialPage: 1,
    initialPageSize: 20
  })

  // 状态
  const videos = ref<Video[]>([])
  const loading = ref(false)
  const statusFilter = ref<number | null>(null)
  const categories = ref<Category[]>([])

  /**
   * 加载视频列表
   */
  const loadVideos = async () => {
    loading.value = true
    try {
      const response = await getMyVideos({
        page: pagination.currentPage.value,
        page_size: pagination.pageSize.value,
        status: statusFilter.value ?? undefined,
      })
      if (response.success) {
        const data = response.data as PageResult<Video>
        videos.value = data.items || []
        pagination.setTotal(data.total || 0)
      }
    } catch (error) {
      console.error('加载视频列表失败:', error)
      ElMessage.error('加载视频列表失败')
    } finally {
      loading.value = false
    }
  }

  /**
   * 加载分类列表
   */
  const loadCategories = async () => {
    try {
      const response = await getCategories()
      if (response && response.data && Array.isArray(response.data)) {
        categories.value = response.data as Category[]
      } else if (Array.isArray(response)) {
        categories.value = response as Category[]
      }
    } catch (error) {
      console.error('加载分类失败:', error)
    }
  }

  /**
   * 状态筛选变化
   */
  const handleStatusChange = (status: number | null) => {
    statusFilter.value = status
    pagination.setPage(1)
    loadVideos()
  }

  /**
   * 查看视频
   */
  const viewVideo = (videoId: number) => {
    router.push(`/videos/${videoId}`)
  }

  /**
   * 删除视频
   */
  const deleteVideoItem = async (video: Video) => {
    try {
      await deleteVideo(video.id)
      ElMessage.success('删除成功')
      await loadVideos()
    } catch (error) {
      if (error !== 'cancel') {
        console.error('删除失败:', error)
        ElMessage.error('删除失败，请重试')
      }
    }
  }

  /**
   * 更新视频信息
   */
  const updateVideoInfo = async (
    videoId: number,
    data: VideoUpdateData & {
      cover_file?: File | null
      subtitle_file?: File | null
    }
  ) => {
    try {
      // 1. 先更新基本信息
      await updateVideo(videoId, {
        title: data.title,
        description: data.description,
        category_id: data.category_id || 0, // 0表示设置为临时分类
      })

      // 2. 上传封面（如果有新封面）
      if (data.cover_file) {
        await uploadVideoCover(videoId, data.cover_file)
      }

      // 3. 上传字幕（如果有新字幕）
      if (data.subtitle_file) {
        await uploadVideoSubtitle(videoId, data.subtitle_file)
      }

      ElMessage.success('更新成功')
      await loadVideos()
      return true
    } catch (error) {
      console.error('更新失败:', error)
      ElMessage.error('更新失败，请重试')
      return false
    }
  }

  /**
   * 生成视频章节大纲
   */
  const generateOutline = async (video: Video) => {
    if (!video.subtitle_url) {
      ElMessage.warning('该视频没有字幕文件，无法生成章节大纲')
      return false
    }

    try {
      ElMessage.info('正在生成章节大纲，请稍候...')
      const response = await generateVideoOutline(video.id)
      if (response.success) {
        ElMessage.success('大纲生成任务已启动，请稍后刷新查看结果')
        // 延迟后刷新视频列表
        setTimeout(async () => {
          await loadVideos()
        }, 3000)
        return true
      } else {
        ElMessage.error('启动大纲生成任务失败')
        return false
      }
    } catch (error: any) {
      console.error('生成章节大纲失败:', error)
      const errorMsg = error?.response?.data?.detail || error?.message || '生成章节大纲失败，请重试'
      ElMessage.error(errorMsg)
      return false
    }
  }

  return {
    // 状态
    videos,
    loading,
    statusFilter,
    categories,
    
    // 分页（从 usePagination 导出）
    currentPage: pagination.currentPage,
    pageSize: pagination.pageSize,
    total: pagination.total,
    totalPages: pagination.totalPages,
    hasMore: pagination.hasMore,
    
    // 方法
    loadVideos,
    loadCategories,
    handleStatusChange,
    viewVideo,
    deleteVideoItem,
    updateVideoInfo,
    generateOutline,
    
    // 分页方法
    setPage: pagination.setPage,
    nextPage: pagination.nextPage,
    prevPage: pagination.prevPage,
  }
}

