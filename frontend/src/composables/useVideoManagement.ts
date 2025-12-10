/**
 * 视频管理 Composable
 * 提取视频管理相关的业务逻辑
 */
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  getMyVideos, 
  updateVideo, 
  deleteVideo, 
  uploadVideoCover, 
  uploadVideoSubtitle 
} from '@/api/video'
import { getCategories } from '@/api/category'
import type { Video, Category, PageResult, VideoUpdateData } from '@/types/entity'

export function useVideoManagement() {
  const router = useRouter()

  // 状态
  const videos = ref<Video[]>([])
  const loading = ref(false)
  const currentPage = ref(1)
  const pageSize = ref(20)
  const total = ref(0)
  const statusFilter = ref<number | null>(null)
  const categories = ref<Category[]>([])

  /**
   * 加载视频列表
   */
  const loadVideos = async () => {
    loading.value = true
    try {
      const response = await getMyVideos({
        page: currentPage.value,
        page_size: pageSize.value,
        status: statusFilter.value,
      })
      if (response.success) {
        const data = response.data as PageResult<Video>
        videos.value = data.items || []
        total.value = data.total || 0
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
  const handleStatusChange = () => {
    currentPage.value = 1
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
      await ElMessageBox.confirm(
        `确定要删除视频"${video.title}"吗？此操作不可恢复！`,
        '警告',
        {
          confirmButtonText: '确定删除',
          cancelButtonText: '取消',
          type: 'error',
          confirmButtonClass: 'el-button--danger',
        }
      )
      await deleteVideo(video.id, true) // hardDelete = true，直接删除数据库记录
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
        category_id: data.category_id || undefined,
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

  return {
    // 状态
    videos,
    loading,
    currentPage,
    pageSize,
    total,
    statusFilter,
    categories,
    
    // 方法
    loadVideos,
    loadCategories,
    handleStatusChange,
    viewVideo,
    deleteVideoItem,
    updateVideoInfo,
  }
}

