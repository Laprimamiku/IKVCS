<template>
  <div class="recommend-section">
    <div class="rec-header">推荐视频</div>
    <div class="recommend-list">
      <div
        v-for="video in videos"
        :key="video.id"
        class="recommend-item"
        @click="$emit('select', video.id)"
      >
        <div class="cover-wrapper">
          <img
            :src="getCoverUrl(video.cover)"
            loading="lazy"
            class="cover-img"
            :alt="video.title"
          />
        </div>
        <div class="info">
          <div class="title" :title="video.title">{{ video.title }}</div>
          <div class="uploader">{{ video.uploader }}</div>
          <div class="stats">{{ formatNumber(video.views) }}播放</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { RecommendVideo } from "@/shared/types/entity";
import { formatNumber, getCoverUrl } from "@/features/video/player/utils/videoFormatters";

defineProps<{
  videos: RecommendVideo[];
}>();

defineEmits<{
  select: [id: number];
}>();
</script>

<style lang="scss" scoped>
.recommend-section {
  .rec-header {
    font-size: 16px;
    font-weight: 500;
    margin-bottom: 12px;
  }

  .recommend-list {
    display: flex;
    flex-direction: column;
    gap: 12px;

    .recommend-item {
      display: flex;
      gap: 10px;
      cursor: pointer;

      &:hover .info .title {
        color: #00aeec;
      }

      .cover-wrapper {
        position: relative;
        width: 140px;
        height: 80px;
        border-radius: 4px;
        overflow: hidden;
        flex-shrink: 0;
        background: #f1f2f3;

        .cover-img {
          width: 100%;
          height: 100%;
          object-fit: cover;
        }
      }

      .info {
        flex: 1;
        min-width: 0;

        .title {
          font-size: 14px;
          color: #18191c;
          line-height: 1.4;
          margin-bottom: 4px;
          display: -webkit-box;
          line-clamp: 2;
          -webkit-line-clamp: 2;
          -webkit-box-orient: vertical;
          overflow: hidden;
          transition: color 0.2s;
        }

        .uploader,
        .stats {
          font-size: 12px;
          color: #9499a0;
          margin-top: 2px;
        }
      }
    }
  }
}

@media (max-width: 1100px) {
  .recommend-list {
    display: grid !important;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  }

  .recommend-item .cover-wrapper {
    width: 160px;
    height: 90px;
  }
}
</style>
