<template>
  <div class="video-card" @click="handleClick">
    <!-- 视频封面区域 -->
    <div class="video-card__cover">
      <!-- 封面图片 -->
      <div class="cover-image">
        <img 
          v-if="video.cover" 
          :src="video.cover" 
          :alt="video.title"
          loading="lazy"
        />
        <div v-else class="cover-placeholder">
          <el-icon :size="48"><VideoPlay /></el-icon>
        </div>
      </div>
      
      <!-- 视频时长 -->
      <span v-if="video.duration" class="video-duration">
        {{ video.duration }}
      </span>
      
      <!-- 视频标签（左上角） -->
      <div v-if="video.tags && video.tags.length" class="video-tags">
        <span 
          v-for="tag in video.tags.slice(0, 2)" 
          :key="tag" 
          class="tag"
          :class="`tag--${tag.toLowerCase()}`"
        >
          {{ tag }}
        </span>
      </div>
      



      <!-- 播放量、弹幕数和点赞数（右上角） -->
      <div class="video-stats">
        <span class="stat-item">
          <el-icon><View /></el-icon>
          <span>{{ formatNumber(video.views) }}</span>
        </span>
        <span class="stat-item">
          <el-icon><ChatDotRound /></el-icon>
          <span>{{ formatNumber(video.danmaku) }}</span>
        </span>
        <span class="stat-item">
          <el-icon><Star /></el-icon>
          <span>{{ formatNumber(video.likes) }}</span>
        </span>
      </div>

      
      <!-- 悬停时显示的操作按钮 -->
      <div class="video-actions">
        <button class="action-btn" @click.stop="handleWatchLater">
          <el-icon><Clock /></el-icon>
          <span>稍后再看</span>
        </button>
      </div>
      
      <!-- 遮罩层 -->
      <div class="cover-overlay"></div>
    </div>
    
    <!-- 视频信息区域 -->
    <div class="video-card__info">
      <!-- 视频标题 -->
      <h3 class="video-title" :title="video.title">
        {{ video.title }}
      </h3>
      
      <!-- UP主信息 -->
      <div class="video-meta">
        <div class="uploader-info">
          <el-avatar 
            :src="video.author?.avatar" 
            :size="20"
            class="uploader-avatar"
          />
          <span class="uploader-name">{{ video.author?.name }}</span>
          <!-- 认证标识 -->
          <el-icon 
            v-if="video.author?.verified" 
            class="verified-icon"
            :title="video.author.verifiedType === 'personal' ? '个人认证' : '企业认证'"
          >
            <CircleCheck />
          </el-icon>
        </div>
        
        <!-- 发布时间 -->
        <span v-if="video.publishTime" class="publish-time">
          {{ formatTime(video.publishTime) }}
        </span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { VideoPlay, View, ChatDotRound, Clock, CircleCheck } from '@element-plus/icons-vue'
import { VideoPlay, View, ChatDotRound, Clock, CircleCheck, Star } from '@element-plus/icons-vue'


const props = defineProps({
  video: {
    type: Object,
    required: true,
    default: () => ({
      id: '',
      title: '',
      cover: '',
      duration: '',
      views: 0,
      danmaku: 0,
      author: {
        name: '',
        avatar: '',
        verified: false,
        verifiedType: 'personal' // 'personal' | 'enterprise'
      },
      tags: [],
      publishTime: ''
    })
  }
})

const emit = defineEmits(['click', 'watch-later'])

/**
 * 格式化数字（播放量、弹幕数）
 */
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

/**
 * 格式化时间
 */
const formatTime = (time) => {
  if (!time) return ''
  const now = new Date()
  const publishDate = new Date(time)
  const diff = now - publishDate
  
  const minute = 60 * 1000
  const hour = 60 * minute
  const day = 24 * hour
  const month = 30 * day
  
  if (diff < hour) {
    return Math.floor(diff / minute) + '分钟前'
  } else if (diff < day) {
    return Math.floor(diff / hour) + '小时前'
  } else if (diff < month) {
    return Math.floor(diff / day) + '天前'
  } else {
    return publishDate.toLocaleDateString('zh-CN')
  }
}

/**
 * 点击卡片
 */
const handleClick = () => {
  emit('click', props.video)
}

/**
 * 稍后再看
 */
const handleWatchLater = () => {
  emit('watch-later', props.video)
}
</script>

<style scoped>
.video-card {
  background: var(--bg-white);
  border-radius: var(--radius-md);
  overflow: hidden;
  cursor: pointer;
  transition: all var(--transition-base);
  height: 100%;
  display: flex;
  flex-direction: column;
}

.video-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-hover);
}

/* ==================== 封面区域 ==================== */
.video-card__cover {
  position: relative;
  width: 100%;
  padding-top: 62.5%; /* 16:10 宽高比 */
  overflow: hidden;
  background: var(--bg-light);
  border-radius: var(--radius-md) var(--radius-md) 0 0;
}

.cover-image {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  transition: transform var(--transition-base);
}

.cover-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.video-card:hover .cover-image {
  transform: scale(1.05);
}

.cover-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-placeholder);
  background: var(--bg-light);
}

/* 遮罩层 */
.cover-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(
    to bottom,
    rgba(0, 0, 0, 0) 0%,
    rgba(0, 0, 0, 0) 50%,
    rgba(0, 0, 0, 0.3) 100%
  );
  opacity: 0;
  transition: opacity var(--transition-base);
  pointer-events: none;
}

.video-card:hover .cover-overlay {
  opacity: 1;
}

/* ==================== 视频时长 ==================== */
.video-duration {
  position: absolute;
  bottom: 8px;
  right: 8px;
  padding: 2px 6px;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(4px);
  color: var(--text-white);
  font-size: var(--font-size-xs);
  border-radius: var(--radius-sm);
  z-index: 2;
}

/* ==================== 视频标签 ==================== */
.video-tags {
  position: absolute;
  top: 8px;
  left: 8px;
  display: flex;
  gap: 4px;
  z-index: 2;
}

.tag {
  padding: 2px 6px;
  font-size: var(--font-size-xs);
  font-weight: 500;
  border-radius: var(--radius-sm);
  backdrop-filter: blur(4px);
}

.tag--4k {
  background: rgba(251, 114, 153, 0.9);
  color: var(--text-white);
}

.tag--hot,
.tag--热门 {
  background: rgba(255, 106, 0, 0.9);
  color: var(--text-white);
}

.tag--new,
.tag--最新 {
  background: rgba(0, 161, 214, 0.9);
  color: var(--text-white);
}

.tag--exclusive,
.tag--独家 {
  background: rgba(255, 185, 0, 0.9);
  color: var(--text-primary);
}

/* ==================== 播放量和弹幕数 ==================== */
.video-stats {
  position: absolute;
  top: 8px;
  right: 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  z-index: 2;
  opacity: 0;
  transform: translateX(10px);
  transition: all var(--transition-base);
}

.video-card:hover .video-stats {
  opacity: 1;
  transform: translateX(0);
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 2px 6px;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(4px);
  color: var(--text-white);
  font-size: var(--font-size-xs);
  border-radius: var(--radius-sm);
}

.stat-item .el-icon {
  font-size: 14px;
}

/* ==================== 操作按钮 ==================== */
.video-actions {
  position: absolute;
  bottom: 12px;
  left: 50%;
  transform: translateX(-50%) translateY(10px);
  opacity: 0;
  transition: all var(--transition-base);
  z-index: 3;
}

.video-card:hover .video-actions {
  opacity: 1;
  transform: translateX(-50%) translateY(0);
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(8px);
  border: none;
  border-radius: var(--radius-lg);
  color: var(--text-primary);
  font-size: var(--font-size-sm);
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-fast);
  box-shadow: var(--shadow-base);
}

.action-btn:hover {
  background: var(--primary-color);
  color: var(--text-white);
  transform: scale(1.05);
}

.action-btn .el-icon {
  font-size: 16px;
}

/* ==================== 信息区域 ==================== */
.video-card__info {
  padding: 12px;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.video-title {
  font-size: var(--font-size-base);
  font-weight: 500;
  color: var(--text-primary);
  line-height: 1.4;
  margin: 0;
  
  /* 两行省略 */
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  overflow: hidden;
  text-overflow: ellipsis;
  word-break: break-word;
  
  transition: color var(--transition-fast);
}

.video-card:hover .video-title {
  color: var(--primary-color);
}

/* ==================== UP主信息 ==================== */
.video-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-top: auto;
}

.uploader-info {
  display: flex;
  align-items: center;
  gap: 6px;
  flex: 1;
  min-width: 0;
}

.uploader-avatar {
  flex-shrink: 0;
}

.uploader-name {
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  transition: color var(--transition-fast);
}

.video-card:hover .uploader-name {
  color: var(--text-regular);
}

.verified-icon {
  flex-shrink: 0;
  font-size: 14px;
  color: var(--primary-color);
}

.publish-time {
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
  white-space: nowrap;
  flex-shrink: 0;
}

/* ==================== 响应式设计 ==================== */
@media (max-width: 768px) {
  .video-card__info {
    padding: 10px;
  }
  
  .video-title {
    font-size: var(--font-size-sm);
  }
  
  .video-actions {
    display: none;
  }
}
</style>
