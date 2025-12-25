<template>
  <div class="bili-video-card" @click="emit('click', video)">
    <!-- Cover Section -->
    <div class="card-cover">
      <div class="cover-image">
        <img
          :src="getCoverUrl(video.cover_url)"
          :alt="video.title"
          loading="lazy"
          @error="handleImageError"
        />
      </div>
      
      <!-- Gradient Mask -->
      <div class="cover-mask"></div>
      
      <!-- Stats Bar -->
      <div class="stats-bar">
        <div class="stats-left">
          <span class="stat-item">
            <el-icon><VideoPlay /></el-icon>
            <span>{{ formatNumber(video.view_count) }}</span>
          </span>
          <span class="stat-item">
            <el-icon><ChatDotRound /></el-icon>
            <span>{{ formatNumber(video.danmaku_count || 0) }}</span>
          </span>
        </div>
        <span class="duration">{{ formatDuration(video.duration) }}</span>
      </div>
      
      <!-- Hover Preview Overlay -->
      <div class="hover-overlay">
        <div class="play-icon">
          <el-icon :size="40"><VideoPlay /></el-icon>
        </div>
      </div>
      
      <!-- Watch Later Button -->
      <div class="watch-later" @click.stop="handleWatchLater">
        <el-icon><Clock /></el-icon>
      </div>
    </div>

    <!-- Info Section -->
    <div class="card-info">
      <h3 class="video-title" :title="video.title">{{ video.title }}</h3>
      <div class="video-meta">
        <div class="uploader" @click.stop="goToUploader">
          <el-icon class="up-icon"><User /></el-icon>
          <span class="up-name">{{ video.uploader?.nickname || '未知UP主' }}</span>
        </div>
        <span class="publish-time">{{ formatDate(video.created_at) }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { VideoPlay, ChatDotRound, User, Clock } from "@element-plus/icons-vue";
import { useRouter } from "vue-router";
import type { Video } from "@/shared/types/entity";

const props = defineProps<{ video: Video }>();
const emit = defineEmits(["click"]);
const router = useRouter();

// Format view/danmaku count
const formatNumber = (num: number): string => {
  if (!num) return "0";
  if (num >= 100000000) return (num / 100000000).toFixed(1) + "亿";
  if (num >= 10000) return (num / 10000).toFixed(1) + "万";
  return num.toString();
};

// Format video duration
const formatDuration = (seconds: number): string => {
  if (!seconds) return "00:00";
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  
  if (h > 0) {
    return `${h}:${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  }
  return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
};

// Format publish date
const formatDate = (dateStr: string): string => {
  if (!dateStr) return "";
  
  const date = new Date(dateStr);
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);
  
  if (minutes < 1) return "刚刚";
  if (minutes < 60) return `${minutes}分钟前`;
  if (hours < 24) return `${hours}小时前`;
  if (days < 7) return `${days}天前`;
  if (days < 30) return `${Math.floor(days / 7)}周前`;
  
  // Show date for older content
  const month = date.getMonth() + 1;
  const day = date.getDate();
  
  if (date.getFullYear() === now.getFullYear()) {
    return `${month}-${day}`;
  }
  return `${date.getFullYear()}-${month}-${day}`;
};

// Get cover URL with fallback
const getCoverUrl = (coverUrl: string | undefined): string => {
  if (!coverUrl) {
    return "https://via.placeholder.com/320x180/f1f2f3/9499a0?text=No+Cover";
  }
  // Add cache buster for fresh images
  return coverUrl.includes("?") ? coverUrl : `${coverUrl}?t=${Date.now()}`;
};

// Handle image load error
const handleImageError = (e: Event) => {
  const img = e.target as HTMLImageElement;
  img.src = "https://via.placeholder.com/320x180/f1f2f3/9499a0?text=No+Cover";
};

// Navigate to uploader profile
const goToUploader = () => {
  if (props.video.uploader?.id) {
    router.push(`/users/${props.video.uploader.id}`);
  }
};

// Add to watch later (placeholder)
const handleWatchLater = () => {
  console.log("Add to watch later:", props.video.id);
};
</script>

<style lang="scss" scoped>
.bili-video-card {
  display: flex;
  flex-direction: column;
  width: 100%;
  cursor: pointer;
  transition: var(--transition-base);
  
  &:hover {
    .card-cover {
      .cover-image img {
        transform: scale(1.05);
      }
      
      .hover-overlay {
        opacity: 1;
      }
      
      .watch-later {
        opacity: 1;
        transform: translateY(0);
      }
    }
    
    .video-title {
      color: var(--bili-pink);
    }
  }
}

/* Cover Section */
.card-cover {
  position: relative;
  width: 100%;
  padding-top: 56.25%; /* 16:9 aspect ratio */
  border-radius: var(--radius-md);
  overflow: hidden;
  background: var(--bg-gray-1);
  
  .cover-image {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    
    img {
      width: 100%;
      height: 100%;
      object-fit: cover;
      transition: transform 0.3s ease;
    }
  }
  
  .cover-mask {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    height: 60px;
    background: linear-gradient(transparent, rgba(0, 0, 0, 0.6));
    pointer-events: none;
    z-index: 1;
  }
}

/* Stats Bar */
.stats-bar {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-2) var(--space-3);
  color: var(--text-white);
  font-size: var(--font-size-xs);
  z-index: 2;
  
  .stats-left {
    display: flex;
    align-items: center;
    gap: var(--space-3);
  }
  
  .stat-item {
    display: flex;
    align-items: center;
    gap: 4px;
    
    .el-icon {
      font-size: 14px;
    }
  }
  
  .duration {
    padding: 2px 6px;
    background: rgba(0, 0, 0, 0.5);
    border-radius: var(--radius-sm);
    font-size: 11px;
  }
}

/* Hover Overlay */
.hover-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.3);
  opacity: 0;
  transition: opacity var(--transition-base);
  z-index: 3;
  
  .play-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 60px;
    height: 60px;
    background: rgba(255, 255, 255, 0.9);
    border-radius: 50%;
    color: var(--bili-pink);
    transition: transform var(--transition-base);
    
    &:hover {
      transform: scale(1.1);
    }
  }
}

/* Watch Later Button */
.watch-later {
  position: absolute;
  top: var(--space-2);
  right: var(--space-2);
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  background: rgba(0, 0, 0, 0.6);
  border-radius: var(--radius-sm);
  color: var(--text-white);
  opacity: 0;
  transform: translateY(-5px);
  transition: all var(--transition-base);
  z-index: 4;
  
  &:hover {
    background: var(--bili-pink);
  }
}

/* Info Section */
.card-info {
  padding: var(--space-3) var(--space-1) 0;
}

.video-title {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-medium);
  color: var(--text-primary);
  line-height: 1.4;
  height: 2.8em; /* 2 lines */
  margin: 0 0 var(--space-2);
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  transition: color var(--transition-fast);
}

.video-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
}

.uploader {
  display: flex;
  align-items: center;
  gap: 4px;
  max-width: 60%;
  transition: color var(--transition-fast);
  
  .up-icon {
    font-size: 12px;
    flex-shrink: 0;
  }
  
  .up-name {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  
  &:hover {
    color: var(--bili-pink);
  }
}

.publish-time {
  flex-shrink: 0;
}

/* Responsive */
@media (max-width: 768px) {
  .video-title {
    font-size: var(--font-size-sm);
  }
  
  .stats-bar {
    padding: var(--space-1) var(--space-2);
    
    .stat-item {
      gap: 2px;
      
      .el-icon {
        font-size: 12px;
      }
    }
  }
  
  .hover-overlay {
    display: none;
  }
  
  .watch-later {
    display: none;
  }
}
</style>
