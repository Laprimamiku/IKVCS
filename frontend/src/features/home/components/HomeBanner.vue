<template>
  <div class="bili-banner">
    <el-carousel
      ref="carouselRef"
      :interval="5000"
      height="100%"
      arrow="never"
      indicator-position="none"
      @change="handleChange"
    >
      <el-carousel-item v-for="(item, index) in banners" :key="index">
        <div class="banner-slide" @click="$emit('click', item)">
          <div
            class="slide-bg"
            :style="{ backgroundImage: `url(${item.image})` }"
          ></div>
          <div class="slide-overlay"></div>
          <div class="slide-content">
            <h3 class="slide-title">{{ item.title }}</h3>
            <p v-if="item.description" class="slide-desc">{{ item.description }}</p>
          </div>
        </div>
      </el-carousel-item>
    </el-carousel>

    <!-- Custom Indicators -->
    <div class="banner-dots">
      <span
        v-for="(item, index) in banners"
        :key="index"
        class="dot"
        :class="{ active: currentIndex === index }"
        @click="goToSlide(index)"
        @mouseenter="pauseAutoplay"
        @mouseleave="resumeAutoplay"
      ></span>
    </div>

    <!-- Navigation Arrows -->
    <div class="banner-nav">
      <div class="nav-btn prev" @click="prev">
        <el-icon><ArrowLeft /></el-icon>
      </div>
      <div class="nav-btn next" @click="next">
        <el-icon><ArrowRight /></el-icon>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { ArrowLeft, ArrowRight } from "@element-plus/icons-vue";
import type { CarouselInstance } from "element-plus";

interface BannerItem {
  id: number;
  title: string;
  description?: string;
  image: string;
  link: string;
}

const props = withDefaults(defineProps<{
  banners?: BannerItem[];
}>(), {
  banners: () => [],
});

const emit = defineEmits<{
  click: [item: BannerItem];
}>();

const carouselRef = ref<CarouselInstance>();
const currentIndex = ref(0);

const handleChange = (index: number) => {
  currentIndex.value = index;
};

const goToSlide = (index: number) => {
  carouselRef.value?.setActiveItem(index);
};

const prev = () => {
  carouselRef.value?.prev();
};

const next = () => {
  carouselRef.value?.next();
};

const pauseAutoplay = () => {
  // Carousel will pause on hover by default
};

const resumeAutoplay = () => {
  // Carousel will resume on mouse leave
};
</script>

<style lang="scss" scoped>
.bili-banner {
  position: relative;
  width: 100%;
  height: 100%;
  border-radius: var(--radius-lg);
  overflow: hidden;
  background: var(--bg-gray-1);

  &:hover {
    .banner-nav .nav-btn {
      opacity: 1;
    }
  }
}

/* Carousel Override */
:deep(.el-carousel) {
  height: 100% !important;
}

:deep(.el-carousel__container) {
  height: 100% !important;
}

:deep(.el-carousel__item) {
  height: 100% !important;
}

/* Banner Slide */
.banner-slide {
  position: relative;
  width: 100%;
  height: 100%;
  cursor: pointer;
}

.slide-bg {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-size: cover;
  background-position: center;
  transition: transform 0.5s ease;
}

.banner-slide:hover .slide-bg {
  transform: scale(1.03);
}

.slide-overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 50%;
  background: linear-gradient(transparent, rgba(0, 0, 0, 0.7));
  pointer-events: none;
}

.slide-content {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: var(--space-6);
  color: var(--text-white);
  z-index: 1;
}

.slide-title {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-semibold);
  margin: 0 0 var(--space-2);
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
}

.slide-desc {
  font-size: var(--font-size-sm);
  margin: 0;
  opacity: 0.9;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
}

/* Custom Dots */
.banner-dots {
  position: absolute;
  bottom: var(--space-4);
  right: var(--space-4);
  display: flex;
  gap: var(--space-2);
  z-index: 2;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: var(--radius-circle);
  background: rgba(255, 255, 255, 0.5);
  cursor: pointer;
  transition: all var(--transition-base);

  &:hover {
    background: rgba(255, 255, 255, 0.8);
  }

  &.active {
    width: 20px;
    border-radius: var(--radius-round);
    background: var(--text-white);
  }
}

/* Navigation Arrows */
.banner-nav {
  .nav-btn {
    position: absolute;
    top: 50%;
    transform: translateY(-50%);
    display: flex;
    align-items: center;
    justify-content: center;
    width: 36px;
    height: 36px;
    background: rgba(0, 0, 0, 0.3);
    border-radius: var(--radius-circle);
    color: var(--text-white);
    cursor: pointer;
    opacity: 0;
    transition: all var(--transition-base);
    z-index: 2;

    &:hover {
      background: rgba(0, 0, 0, 0.5);
    }

    &.prev {
      left: var(--space-3);
    }

    &.next {
      right: var(--space-3);
    }
  }
}

/* Responsive */
@media (max-width: 768px) {
  .slide-content {
    padding: var(--space-4);
  }

  .slide-title {
    font-size: var(--font-size-lg);
  }

  .slide-desc {
    font-size: var(--font-size-xs);
  }

  .banner-dots {
    bottom: var(--space-3);
    right: var(--space-3);
  }

  .banner-nav .nav-btn {
    width: 28px;
    height: 28px;
    opacity: 1;
  }
}
</style>
