<template>
  <div class="bili-video-card" @click="emit('click', video)">
    <div class="card-cover">
      <img
        :src="getCoverUrl(video.cover_url)"
        :alt="video.title"
        loading="lazy"
      />

      <div class="stats-bar">
        <div class="left">
          <span class="stat-item">
            <el-icon><VideoPlay /></el-icon>
            {{ formatNumber(video.view_count) }}
          </span>
          <span class="stat-item">
            <el-icon><ChatDotRound /></el-icon>
            {{ formatNumber(video.danmaku_count || 0) }}
          </span>
        </div>
        <span class="duration">{{ formatDuration(video.duration) }}</span>
      </div>
    </div>

    <div class="card-info">
      <h3 class="title" :title="video.title">{{ video.title }}</h3>
      <div class="meta">
        <a class="up-name" @click.stop>
          <el-icon><User /></el-icon> {{ video.uploader.nickname }}
        </a>
        <span class="date">{{ formatDate(video.created_at) }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { VideoPlay, ChatDotRound, User } from "@element-plus/icons-vue";
import type { Video } from "@/shared/types/entity";
// 定义 Props 类型
defineProps<{
  video: Video;
}>();

const emit = defineEmits(["click"]);

const formatNumber = (num: number) => {
  if (num >= 10000) return (num / 10000).toFixed(1) + "万";
  return num;
};

const formatDuration = (seconds: number) => {
  const m = Math.floor(seconds / 60)
    .toString()
    .padStart(2, "0");
  const s = (seconds % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
};

const formatDate = (dateStr: string) => {
  const date = new Date(dateStr);
  const now = new Date();
  // 简单处理：如果是今天则显示时间，否则显示日期
  return date.toLocaleDateString();
};

// 获取封面URL，添加时间戳防止缓存（API层已处理URL，这里只需添加时间戳）
const getCoverUrl = (coverUrl: string | undefined): string => {
  if (!coverUrl) return '';
  // 添加时间戳防止缓存
  return `${coverUrl}?t=${Date.now()}`;
};
</script>

<style lang="scss" scoped>
.bili-video-card {
  display: flex;
  flex-direction: column;
  cursor: pointer;
  transition: transform 0.2s;

  &:hover {
    transform: translateY(-2px);
  }

  .card-cover {
    position: relative;
    width: 100%;
    padding-top: 56.25%; // 16:9 比例
    border-radius: var(--radius-md);
    overflow: hidden;
    background-color: var(--bg-global);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
    transition: box-shadow 0.2s;

    &:hover {
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
    }

    img {
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      object-fit: cover;
      transition: transform 0.3s ease-out;
    }

    // 悬停时图片微放大
    &:hover img {
      transform: scale(1.05);
    }

    .stats-bar {
      position: absolute;
      bottom: 0;
      left: 0;
      right: 0;
      height: 36px;
      padding: 0 10px;
      background: linear-gradient(180deg, transparent 0%, rgba(0, 0, 0, 0.6) 100%);
      display: flex;
      align-items: center;
      justify-content: space-between;
      color: #fff;
      font-size: 12px;
      font-weight: 500;

      .left {
        display: flex;
        gap: 12px;
        align-items: center;

        .stat-item {
          display: flex;
          align-items: center;
          gap: 4px;
          opacity: 0.9;

          .el-icon {
            font-size: 14px;
          }
        }
      }

      .duration {
        background: rgba(0, 0, 0, 0.6);
        padding: 2px 6px;
        border-radius: var(--radius-sm);
        font-weight: 500;
        letter-spacing: 0.5px;
      }
    }
  }

  .card-info {
    margin-top: 10px;
    padding: 0 2px;

    .title {
      font-size: 14px;
      color: var(--text-primary);
      line-height: 20px;
      height: 40px; // 限制两行高度
      overflow: hidden;
      text-overflow: ellipsis;
      display: -webkit-box;
      line-clamp: 2;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      font-weight: 500;
      margin-bottom: 6px;
      transition: color 0.2s;

      // 悬停标题变色
      &:hover {
        color: var(--primary-color);
      }
    }

    .meta {
      display: flex;
      align-items: center;
      justify-content: space-between;
      color: var(--text-tertiary);
      font-size: 12px;

      .up-name {
        display: flex;
        align-items: center;
        gap: 4px;
        text-decoration: none;
        color: var(--text-tertiary);
        transition: color 0.2s;

        .el-icon {
          font-size: 14px;
        }

        &:hover {
          color: var(--primary-color);
        }
      }

      .date {
        color: var(--text-tertiary);
      }
    }
  }
}
</style>
