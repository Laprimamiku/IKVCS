<template>
  <div class="video-grid">
    <VideoCard
      v-for="video in videos"
      :key="video.id"
      :video="video"
      @click="$emit('video-click', video)"
    />
  </div>
</template>

<script setup lang="ts">
import VideoCard from "./VideoCard.vue";
import type { Video } from "@/types/entity";

defineProps<{
  videos: Video[];
  loading: boolean;
}>();

defineEmits(["video-click", "load-more"]);
</script>

<style lang="scss" scoped>
.video-grid {
  display: grid;
  // B站风格的响应式 Grid
  grid-template-columns: repeat(2, 1fr); // 手机端
  gap: 20px;

  @media (min-width: 640px) {
    grid-template-columns: repeat(3, 1fr);
  }
  @media (min-width: 960px) {
    grid-template-columns: repeat(4, 1fr);
  }
  @media (min-width: 1400px) {
    grid-template-columns: repeat(5, 1fr);
  }
}
</style>
