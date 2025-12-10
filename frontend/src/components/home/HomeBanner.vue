<template>
  <div class="home-banner">
    <el-carousel 
      ref="carouselRef"
      :interval="4000" 
      :height="bannerHeight"
      arrow="hover"
      indicator-position="none"
      @change="handleChange"
    >
      <el-carousel-item 
        v-for="(item, index) in banners" 
        :key="index"
      >
        <div class="banner-item">
          <!-- 背景图片 -->
          <div 
            class="banner-bg"
            :style="{ backgroundImage: `url(${item.image})` }"
          ></div>
          
          <!-- 渐变遮罩 -->
          <div class="banner-overlay"></div>
          
          <!-- 内容区域 -->
          <div class="banner-content">
            <div class="banner-info">
              <h2 class="banner-title">{{ item.title }}</h2>
              <p class="banner-desc">{{ item.description }}</p>
              <div class="banner-actions">
                <el-button 
                  type="primary" 
                  size="large"
                  round
                  @click="handleBannerClick(item)"
                >
                  <el-icon><VideoPlay /></el-icon>
                  <span>立即观看</span>
                </el-button>
              </div>
            </div>
          </div>
        </div>
      </el-carousel-item>
    </el-carousel>
    
    <!-- 自定义指示器 -->
    <div class="banner-indicators">
      <span
        v-for="(item, index) in banners"
        :key="index"
        class="indicator-dot"
        :class="{ 'is-active': currentIndex === index }"
        @click="setActiveItem(index)"
      ></span>
    </div>
    
    <!-- 自定义箭头 -->
    <button 
      class="banner-arrow banner-arrow--left"
      @click="prev"
    >
      <el-icon><ArrowLeft /></el-icon>
    </button>
    <button 
      class="banner-arrow banner-arrow--right"
      @click="next"
    >
      <el-icon><ArrowRight /></el-icon>
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { VideoPlay, ArrowLeft, ArrowRight } from '@element-plus/icons-vue'

const props = defineProps({
  banners: {
    type: Array,
    default: () => [
      {
        id: 1,
        title: '精彩视频推荐',
        description: '发现更多优质内容',
        image: 'https://picsum.photos/1400/400?random=1',
        link: '/video/1'
      },
      {
        id: 2,
        title: '热门番剧',
        description: '追番必看',
        image: 'https://picsum.photos/1400/400?random=2',
        link: '/bangumi/1'
      },
      {
        id: 3,
        title: '音乐专区',
        description: '聆听美妙旋律',
        image: 'https://picsum.photos/1400/400?random=3',
        link: '/music/1'
      }
    ]
  },
  height: {
    type: String,
    default: '400px'
  }
})

const emit = defineEmits(['click'])

const carouselRef = ref(null)
const currentIndex = ref(0)

const bannerHeight = computed(() => props.height)

/**
 * 切换轮播图
 */
const handleChange = (index) => {
  currentIndex.value = index
}

/**
 * 设置当前项
 */
const setActiveItem = (index) => {
  carouselRef.value?.setActiveItem(index)
}

/**
 * 上一张
 */
const prev = () => {
  carouselRef.value?.prev()
}

/**
 * 下一张
 */
const next = () => {
  carouselRef.value?.next()
}

/**
 * 点击轮播图
 */
const handleBannerClick = (item) => {
  emit('click', item)
}

// 响应式高度调整
const updateHeight = () => {
  const width = window.innerWidth
  if (width < 768) {
    return '200px'
  } else if (width < 1200) {
    return '300px'
  }
  return '400px'
}

onMounted(() => {
  window.addEventListener('resize', updateHeight)
})

onUnmounted(() => {
  window.removeEventListener('resize', updateHeight)
})
</script>

<style lang="scss" scoped>
.home-banner {
  position: relative;
  width: 100%;
  margin-bottom: var(--spacing-xl);
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: var(--shadow-base);
}

/* ==================== 轮播项 ==================== */
.banner-item {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
}

/* 背景图片 */
.banner-bg {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
  transition: transform 0.6s ease;
}

.banner-item:hover .banner-bg {
  transform: scale(1.05);
}

/* 渐变遮罩 */
.banner-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: linear-gradient(
    to right,
    rgba(0, 0, 0, 0.7) 0%,
    rgba(0, 0, 0, 0.4) 50%,
    rgba(0, 0, 0, 0.1) 100%
  );
}

/* ==================== 内容区域 ==================== */
.banner-content {
  position: relative;
  height: 100%;
  display: flex;
  align-items: center;
  padding: 0 var(--spacing-3xl);
  z-index: 2;
}

.banner-info {
  max-width: 600px;
  color: var(--text-white);
  animation: fadeInUp 0.8s ease;
}

.banner-title {
  font-size: var(--font-size-3xl);
  font-weight: bold;
  margin: 0 0 var(--spacing-md) 0;
  text-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

.banner-desc {
  font-size: var(--font-size-md);
  margin: 0 0 var(--spacing-xl) 0;
  opacity: 0.9;
  text-shadow: 0 1px 4px rgba(0, 0, 0, 0.3);
}

.banner-actions {
  display: flex;
  gap: var(--spacing-md);
}

.banner-actions .el-button {
  padding: 12px 32px;
  font-size: var(--font-size-md);
  font-weight: 500;
  box-shadow: var(--shadow-base);
  transition: all var(--transition-base);
}

.banner-actions .el-button:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg);
}

/* ==================== 自定义指示器 ==================== */
.banner-indicators {
  position: absolute;
  bottom: var(--spacing-lg);
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  gap: var(--spacing-sm);
  z-index: 3;
}

.indicator-dot {
  width: 8px;
  height: 8px;
  border-radius: var(--radius-round);
  background: rgba(255, 255, 255, 0.5);
  cursor: pointer;
  transition: all var(--transition-base);
}

.indicator-dot:hover {
  background: rgba(255, 255, 255, 0.8);
  transform: scale(1.2);
}

.indicator-dot.is-active {
  width: 24px;
  background: var(--text-white);
}

/* ==================== 自定义箭头 ==================== */
.banner-arrow {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.2);
  backdrop-filter: blur(8px);
  border: none;
  border-radius: var(--radius-round);
  color: var(--text-white);
  font-size: 20px;
  cursor: pointer;
  opacity: 0;
  transition: all var(--transition-base);
  z-index: 3;
}

.home-banner:hover .banner-arrow {
  opacity: 1;
}

.banner-arrow:hover {
  background: rgba(255, 255, 255, 0.3);
  transform: translateY(-50%) scale(1.1);
}

.banner-arrow--left {
  left: var(--spacing-lg);
}

.banner-arrow--right {
  right: var(--spacing-lg);
}

/* ==================== Element Plus 轮播图样式覆盖 ==================== */
.home-banner :deep(.el-carousel__container) {
  height: 100%;
}

.home-banner :deep(.el-carousel__arrow) {
  display: none;
}

/* ==================== 响应式设计 ==================== */
@media (max-width: 1200px) {
  .banner-content {
    padding: 0 var(--spacing-xl);
  }
  
  .banner-title {
    font-size: var(--font-size-2xl);
  }
  
  .banner-desc {
    font-size: var(--font-size-base);
  }
}

@media (max-width: 768px) {
  .banner-content {
    padding: 0 var(--spacing-md);
  }
  
  .banner-title {
    font-size: var(--font-size-xl);
  }
  
  .banner-desc {
    font-size: var(--font-size-sm);
    margin-bottom: var(--spacing-md);
  }
  
  .banner-actions .el-button {
    padding: 10px 24px;
    font-size: var(--font-size-sm);
  }
  
  .banner-arrow {
    width: 36px;
    height: 36px;
    font-size: 16px;
  }
  
  .banner-arrow--left {
    left: var(--spacing-sm);
  }
  
  .banner-arrow--right {
    right: var(--spacing-sm);
  }
}
</style>
