<template>
  <div class="video-grid-container">
    <!-- 视频网格 -->
    <div 
      ref="gridRef"
      class="video-grid"
      :class="{ 'is-loading': loading }"
    >
      <!-- 视频卡片 -->
      <VideoCard
        v-for="video in videos"
        :key="video.id"
        :video="video"
        @click="handleVideoClick"
        @watch-later="handleWatchLater"
      />
      
      <!-- 骨架屏加载 -->
      <div 
        v-if="loading" 
        v-for="n in skeletonCount" 
        :key="`skeleton-${n}`"
        class="video-skeleton"
      >
        <el-skeleton animated>
          <template #template>
            <el-skeleton-item variant="image" class="skeleton-cover" />
            <div class="skeleton-info">
              <el-skeleton-item variant="h3" style="width: 90%" />
              <el-skeleton-item variant="text" style="width: 60%" />
            </div>
          </template>
        </el-skeleton>
      </div>
    </div>
    
    <!-- 加载更多指示器 -->
    <div v-if="hasMore && !loading" class="load-more">
      <el-button 
        type="primary" 
        :loading="loadingMore"
        @click="loadMore"
      >
        {{ loadingMore ? '加载中...' : '加载更多' }}
      </el-button>
    </div>
    
    <!-- 没有更多数据 -->
    <div v-if="!hasMore && videos.length > 0" class="no-more">
      <span>没有更多内容了</span>
    </div>
    
    <!-- 空状态 -->
    <el-empty 
      v-if="!loading && videos.length === 0"
      description="暂无视频"
      :image-size="120"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import VideoCard from './VideoCard.vue'
import { ElMessage } from 'element-plus'

const props = defineProps({
  videos: {
    type: Array,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  },
  hasMore: {
    type: Boolean,
    default: true
  },
  infiniteScroll: {
    type: Boolean,
    default: true
  },
  skeletonCount: {
    type: Number,
    default: 8
  }
})

const emit = defineEmits(['load-more', 'video-click', 'watch-later'])

const gridRef = ref(null)
const loadingMore = ref(false)

/**
 * 加载更多
 */
const loadMore = async () => {
  if (loadingMore.value || !props.hasMore) return
  
  loadingMore.value = true
  try {
    await emit('load-more')
  } finally {
    loadingMore.value = false
  }
}

/**
 * 无限滚动处理
 */
const handleScroll = () => {
  if (!props.infiniteScroll || !props.hasMore || props.loading || loadingMore.value) {
    return
  }
  
  const scrollTop = window.pageYOffset || document.documentElement.scrollTop
  const windowHeight = window.innerHeight
  const documentHeight = document.documentElement.scrollHeight
  
  // 距离底部 300px 时触发加载
  if (scrollTop + windowHeight >= documentHeight - 300) {
    loadMore()
  }
}

/**
 * 节流函数
 */
const throttle = (func, delay) => {
  let timer = null
  return function(...args) {
    if (!timer) {
      timer = setTimeout(() => {
        func.apply(this, args)
        timer = null
      }, delay)
    }
  }
}

const throttledScroll = throttle(handleScroll, 200)

/**
 * 点击视频卡片
 */
const handleVideoClick = (video) => {
  emit('video-click', video)
}

/**
 * 稍后再看
 */
const handleWatchLater = (video) => {
  ElMessage.success(`已添加到稍后再看：${video.title}`)
  emit('watch-later', video)
}

onMounted(() => {
  if (props.infiniteScroll) {
    window.addEventListener('scroll', throttledScroll)
  }
})

onUnmounted(() => {
  if (props.infiniteScroll) {
    window.removeEventListener('scroll', throttledScroll)
  }
})
</script>

<style scoped>
.video-grid-container {
  width: 100%;
}

/* ==================== 视频网格布局 ==================== */
.video-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: var(--video-card-gap);
  margin-bottom: var(--spacing-xl);
}

/* 骨架屏 */
.video-skeleton {
  background: var(--bg-white);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.skeleton-cover {
  width: 100%;
  height: 0;
  padding-top: 62.5%;
}

.skeleton-info {
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* ==================== 加载更多 ==================== */
.load-more {
  display: flex;
  justify-content: center;
  padding: var(--spacing-xl) 0;
}

.load-more .el-button {
  min-width: 120px;
}

/* ==================== 没有更多 ==================== */
.no-more {
  text-align: center;
  padding: var(--spacing-xl) 0;
  color: var(--text-secondary);
  font-size: var(--font-size-sm);
}

.no-more::before,
.no-more::after {
  content: '';
  display: inline-block;
  width: 60px;
  height: 1px;
  background: var(--border-light);
  margin: 0 var(--spacing-md);
  vertical-align: middle;
}

/* ==================== 响应式布局 ==================== */
/* 超大屏幕 (>= 1400px) - 5列 */
@media (min-width: 1400px) {
  .video-grid {
    grid-template-columns: repeat(5, 1fr);
  }
}

/* 大屏幕 (1200px - 1399px) - 4列 */
@media (max-width: 1399px) {
  .video-grid {
    grid-template-columns: repeat(4, 1fr);
  }
}

/* 中等屏幕 (992px - 1199px) - 3列 */
@media (max-width: 1199px) {
  .video-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

/* 小屏幕 (768px - 991px) - 2列 */
@media (max-width: 991px) {
  .video-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: var(--spacing-md);
  }
}

/* 超小屏幕 (< 768px) - 1列 */
@media (max-width: 767px) {
  .video-grid {
    grid-template-columns: 1fr;
    gap: var(--spacing-md);
  }
}
</style>
