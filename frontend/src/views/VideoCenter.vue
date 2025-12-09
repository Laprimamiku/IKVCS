<template>
  <div class="video-center-page">
    <!-- 顶部操作栏 -->
    <div class="header-section">
      <h1 class="page-title">我的视频</h1>
      <el-button type="primary" @click="router.push('/upload')">
        <el-icon><Upload /></el-icon>
        上传视频
      </el-button>
    </div>

    <!-- 状态筛选 -->
    <div class="filter-section">
      <el-radio-group v-model="statusFilter" @change="handleStatusChange">
        <el-radio-button :label="null">全部</el-radio-button>
        <el-radio-button :label="0">转码中</el-radio-button>
        <el-radio-button :label="1">审核中</el-radio-button>
        <el-radio-button :label="2">已发布</el-radio-button>
        <el-radio-button :label="3">已拒绝</el-radio-button>
      </el-radio-group>
    </div>

    <!-- 视频列表 -->
    <div class="video-list">
      <el-empty v-if="!loading && videos.length === 0" description="暂无视频，快去上传吧~" />
      <div v-else class="video-grid">
        <div v-for="video in videos" :key="video.id" class="video-item">
          <!-- 视频封面 -->
          <div class="video-cover" @click="handleView(video.id)">
            <img v-if="video.cover_url" :src="resolveFileUrl(video.cover_url)" alt="封面" />
            <div v-else class="cover-placeholder">
              <el-icon :size="48"><VideoPlay /></el-icon>
            </div>
            <div class="status-badge" :class="getStatusClass(video.status)">
              {{ getStatusText(video.status) }}
            </div>
            <div class="video-duration" v-if="video.duration">
              {{ formatDuration(video.duration) }}
            </div>
          </div>

          <!-- 视频信息 -->
          <div class="video-info">
            <h3 class="video-title" :title="video.title">{{ video.title }}</h3>
            <div class="video-meta">
              <span class="meta-item">
                <el-icon><View /></el-icon>
                {{ formatNumber(video.view_count) }}
              </span>
              <span class="meta-item">
                <el-icon><Star /></el-icon>
                {{ formatNumber(video.like_count) }}
              </span>
              <span class="meta-item">
                <el-icon><Collection /></el-icon>
                {{ formatNumber(video.collect_count) }}
              </span>
            </div>
            <div class="video-actions">
              <el-button size="small" @click="handleView(video.id)">查看</el-button>
              <el-button size="small" type="primary" @click="handleEdit(video)">编辑</el-button>
              <el-button size="small" type="danger" @click="handleDelete(video)">删除</el-button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 分页 -->
    <el-pagination
      v-if="total > 0"
      v-model:current-page="currentPage"
      :page-size="pageSize"
      :total="total"
      layout="total, prev, pager, next"
      @current-change="loadVideos"
      class="pagination"
    />

    <!-- 编辑对话框 -->
    <el-dialog v-model="editDialogVisible" title="编辑视频" width="700px" :close-on-click-modal="false">
      <el-form :model="editForm" :rules="editRules" ref="editFormRef" label-width="80px">
        <el-form-item label="标题" prop="title">
          <el-input v-model="editForm.title" placeholder="请输入视频标题" maxlength="100" show-word-limit />
        </el-form-item>
        
        <el-form-item label="描述" prop="description">
          <el-input 
            v-model="editForm.description" 
            type="textarea" 
            :rows="4" 
            placeholder="请输入视频描述（可选）"
            maxlength="500"
            show-word-limit
          />
        </el-form-item>
        
        <el-form-item label="分类" prop="category_id">
          <el-select v-model="editForm.category_id" placeholder="请选择分类" style="width: 100%">
            <el-option
              v-for="cat in categories"
              :key="cat.id"
              :label="cat.name"
              :value="cat.id"
            />
          </el-select>
        </el-form-item>

        <!-- 封面上传 -->
        <el-form-item label="封面">
          <div class="cover-upload-section">
            <div v-if="editForm.cover_preview" class="cover-preview">
              <img :src="editForm.cover_preview" alt="封面预览" />
              <el-button
                type="danger"
                size="small"
                circle
                class="remove-cover-btn"
                @click="removeCover"
              >
                <el-icon><Close /></el-icon>
              </el-button>
            </div>
            <el-upload
              v-else
              :auto-upload="false"
              :show-file-list="false"
              accept="image/*"
              :on-change="handleCoverChange"
            >
              <el-button type="primary" plain>
                <el-icon><Picture /></el-icon>
                {{ editForm.cover_url ? '更换封面' : '上传封面' }}
              </el-button>
              <template #tip>
                <div class="el-upload__tip">支持 JPG、PNG、WEBP 格式，最大 5MB</div>
              </template>
            </el-upload>
          </div>
        </el-form-item>

        <!-- 字幕上传 -->
        <el-form-item label="字幕">
          <div class="subtitle-upload-section">
            <div v-if="editForm.subtitle_file" class="subtitle-preview">
              <el-icon><Document /></el-icon>
              <span>{{ editForm.subtitle_file.name }}</span>
              <el-button
                type="danger"
                size="small"
                text
                @click="removeSubtitle"
              >
                移除
              </el-button>
            </div>
            <el-upload
              v-else
              :auto-upload="false"
              :show-file-list="false"
              accept=".srt,.vtt,.json,.ass"
              :on-change="handleSubtitleChange"
            >
              <el-button type="primary" plain>
                <el-icon><Document /></el-icon>
                {{ editForm.subtitle_url ? '更换字幕' : '上传字幕' }}
              </el-button>
              <template #tip>
                <div class="el-upload__tip">支持 SRT、VTT、JSON、ASS 格式（可选）</div>
              </template>
            </el-upload>
          </div>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSaveEdit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  Upload, 
  VideoPlay, 
  View, 
  Star, 
  Collection, 
  Picture, 
  Document, 
  Close 
} from '@element-plus/icons-vue'
import { getMyVideos, updateVideo, deleteVideo, uploadVideoCover, uploadVideoSubtitle } from '@/api/video'
import { getCategories } from '@/api/category'

const router = useRouter()

// 数据
const videos = ref([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const statusFilter = ref(null)
const categories = ref([])
const saving = ref(false)

// 编辑相关
const editDialogVisible = ref(false)
const editFormRef = ref(null)
const editForm = reactive({
  id: null,
  title: '',
  description: '',
  category_id: null,
  cover_url: '',
  cover_preview: '',
  cover_file: null,
  subtitle_url: '',
  subtitle_file: null
})

const editRules = {
  title: [
    { required: true, message: '请输入视频标题', trigger: 'blur' },
    { min: 1, max: 100, message: '标题长度在 1 到 100 个字符', trigger: 'blur' }
  ],
  category_id: [
    { required: true, message: '请选择分类', trigger: 'change' }
  ],
  description: [
    { max: 500, message: '描述长度不能超过 500 个字符', trigger: 'blur' }
  ]
}

// 加载视频列表
const loadVideos = async () => {
  loading.value = true
  try {
    const response = await getMyVideos({
      page: currentPage.value,
      page_size: pageSize.value,
      status: statusFilter.value
    })
    if (response.success) {
      videos.value = response.data.items || []
      total.value = response.data.total || 0
    }
  } catch (error) {
    console.error('加载视频列表失败:', error)
    ElMessage.error('加载视频列表失败')
  } finally {
    loading.value = false
  }
}

// 加载分类列表
const loadCategories = async () => {
  try {
    const response = await getCategories()
    if (response && response.data && Array.isArray(response.data)) {
      categories.value = response.data
    } else if (Array.isArray(response)) {
      categories.value = response
    }
  } catch (error) {
    console.error('加载分类失败:', error)
  }
}

// 状态相关方法
const getStatusText = (status) => {
  const map = {
    0: '转码中',
    1: '审核中',
    2: '已发布',
    3: '已拒绝',
    4: '已删除'
  }
  return map[status] || '未知'
}

const getStatusClass = (status) => {
  const map = {
    0: 'status-transcoding',
    1: 'status-reviewing',
    2: 'status-published',
    3: 'status-rejected',
    4: 'status-deleted'
  }
  return map[status] || ''
}

// 文件URL解析
const resolveFileUrl = (path) => {
  if (!path) return ''
  if (path.startsWith('http')) return path
  const base = import.meta.env.VITE_FILE_BASE_URL || 
    (import.meta.env.VITE_API_BASE_URL
      ? import.meta.env.VITE_API_BASE_URL.replace(/\/api\/v1$/, '')
      : window.location.origin)
  return `${base}${path}`
}

// 格式化数字
const formatNumber = (num) => {
  if (!num) return '0'
  if (num >= 100000000) {
    return (num / 100000000).toFixed(1) + '亿'
  }
  if (num >= 10000) {
    return (num / 10000).toFixed(1) + '万'
  }
  return num.toString()
}

// 格式化时长
const formatDuration = (seconds) => {
  if (!seconds) return '00:00'
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const secs = seconds % 60
  if (hours > 0) {
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }
  return `${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
}

// 状态筛选变化
const handleStatusChange = () => {
  currentPage.value = 1
  loadVideos()
}

// 操作处理
const handleView = (videoId) => {
  router.push(`/videos/${videoId}`)
}

const handleEdit = (video) => {
  editForm.id = video.id
  editForm.title = video.title
  editForm.description = video.description || ''
  editForm.category_id = video.category_id
  editForm.cover_url = video.cover_url || ''
  editForm.cover_preview = video.cover_url ? resolveFileUrl(video.cover_url) : ''
  editForm.cover_file = null
  editForm.subtitle_url = video.subtitle_url || ''
  editForm.subtitle_file = null
  editDialogVisible.value = true
}

// 封面上传处理
const handleCoverChange = (file) => {
  // 验证文件类型
  const validTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp']
  if (!validTypes.includes(file.raw.type)) {
    ElMessage.warning('封面格式不支持，仅支持 JPG、PNG、WEBP')
    return
  }
  // 验证文件大小（5MB）
  if (file.raw.size > 5 * 1024 * 1024) {
    ElMessage.warning('封面文件过大，最大 5MB')
    return
  }
  editForm.cover_file = file.raw
  // 预览
  const reader = new FileReader()
  reader.onload = (e) => {
    editForm.cover_preview = e.target.result
  }
  reader.readAsDataURL(file.raw)
}

const removeCover = () => {
  editForm.cover_file = null
  editForm.cover_preview = ''
  editForm.cover_url = ''
}

// 字幕上传处理
const handleSubtitleChange = (file) => {
  const validExts = ['.srt', '.vtt', '.json', '.ass']
  const ext = '.' + file.name.split('.').pop().toLowerCase()
  if (!validExts.includes(ext)) {
    ElMessage.warning('字幕格式不支持，仅支持 SRT、VTT、JSON、ASS')
    return
  }
  editForm.subtitle_file = file.raw
}

const removeSubtitle = () => {
  editForm.subtitle_file = null
  editForm.subtitle_url = ''
}

// 保存编辑
const handleSaveEdit = async () => {
  if (!editFormRef.value) return
  
  await editFormRef.value.validate(async (valid) => {
    if (!valid) return
    
    saving.value = true
    try {
      // 1. 先更新基本信息
      await updateVideo(editForm.id, {
        title: editForm.title,
        description: editForm.description,
        category_id: editForm.category_id
      })
      
      // 2. 上传封面（如果有新封面）
      if (editForm.cover_file) {
        await uploadVideoCover(editForm.id, editForm.cover_file)
      }
      
      // 3. 上传字幕（如果有新字幕）
      if (editForm.subtitle_file) {
        await uploadVideoSubtitle(editForm.id, editForm.subtitle_file)
      }
      
      ElMessage.success('更新成功')
      editDialogVisible.value = false
      loadVideos()
    } catch (error) {
      console.error('更新失败:', error)
      ElMessage.error('更新失败，请重试')
    } finally {
      saving.value = false
    }
  })
}

// 删除视频
const handleDelete = async (video) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除视频"${video.title}"吗？删除后可在回收站恢复。`,
      '提示',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    await deleteVideo(video.id, false)
    ElMessage.success('删除成功')
    loadVideos()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除失败:', error)
      ElMessage.error('删除失败，请重试')
    }
  }
}

onMounted(() => {
  loadCategories()
  loadVideos()
})
</script>

<style scoped>
.video-center-page {
  min-height: 100vh;
  background: var(--bg-light);
  padding: var(--spacing-lg);
}

.header-section {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-lg);
  background: var(--bg-white);
  padding: var(--spacing-lg);
  border-radius: var(--radius-md);
}

.page-title {
  margin: 0;
  font-size: var(--font-size-2xl);
  font-weight: 600;
  color: var(--text-primary);
}

.filter-section {
  margin-bottom: var(--spacing-lg);
  background: var(--bg-white);
  padding: var(--spacing-md);
  border-radius: var(--radius-md);
}

.video-list {
  margin-bottom: var(--spacing-lg);
}

.video-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: var(--spacing-lg);
}

.video-item {
  background: var(--bg-white);
  border-radius: var(--radius-md);
  overflow: hidden;
  transition: all var(--transition-base);
  cursor: pointer;
}

.video-item:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-hover);
}

.video-cover {
  position: relative;
  width: 100%;
  padding-top: 56.25%; /* 16:9 */
  overflow: hidden;
  background: var(--bg-light);
}

.video-cover img {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.cover-placeholder {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-placeholder);
  background: var(--bg-light);
}

.status-badge {
  position: absolute;
  top: 8px;
  left: 8px;
  padding: 4px 10px;
  border-radius: var(--radius-sm);
  font-size: var(--font-size-xs);
  font-weight: 500;
  color: white;
  backdrop-filter: blur(4px);
}

.status-transcoding {
  background: rgba(64, 158, 255, 0.9);
}

.status-reviewing {
  background: rgba(230, 162, 60, 0.9);
}

.status-published {
  background: rgba(103, 194, 58, 0.9);
}

.status-rejected {
  background: rgba(245, 108, 108, 0.9);
}

.status-deleted {
  background: rgba(144, 147, 153, 0.9);
}

.video-duration {
  position: absolute;
  bottom: 8px;
  right: 8px;
  padding: 2px 6px;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(4px);
  color: white;
  font-size: var(--font-size-xs);
  border-radius: var(--radius-sm);
}

.video-info {
  padding: var(--spacing-md);
}

.video-title {
  margin: 0 0 var(--spacing-sm) 0;
  font-size: var(--font-size-base);
  font-weight: 500;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.video-meta {
  display: flex;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-sm);
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.video-actions {
  display: flex;
  gap: var(--spacing-sm);
}

.pagination {
  display: flex;
  justify-content: center;
  margin-top: var(--spacing-lg);
}

/* 编辑对话框样式 */
.cover-upload-section,
.subtitle-upload-section {
  width: 100%;
}

.cover-preview {
  position: relative;
  width: 200px;
  height: 112px;
  border-radius: var(--radius-md);
  overflow: hidden;
  margin-bottom: var(--spacing-sm);
}

.cover-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.remove-cover-btn {
  position: absolute;
  top: 4px;
  right: 4px;
}

.subtitle-preview {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm);
  background: var(--bg-light);
  border-radius: var(--radius-base);
}

/* 响应式 */
@media (max-width: 768px) {
  .video-center-page {
    padding: var(--spacing-md);
  }

  .header-section {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--spacing-md);
  }

  .video-grid {
    grid-template-columns: 1fr;
  }

  .video-actions {
    flex-wrap: wrap;
  }
}
</style>