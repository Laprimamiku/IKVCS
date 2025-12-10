<template>
  <div class="video-player-core">
    <video
      v-if="videoUrl"
      ref="videoRef"
      class="video-element"
      controls
      :src="videoUrl"
      @loadedmetadata="handleLoadedMetadata"
    >
      <track
        v-if="subtitleUrl"
        kind="subtitles"
        :src="subtitleUrl"
        label="中文字幕"
        srclang="zh"
        default
      />
      您的浏览器不支持视频播放。
    </video>
    <div v-else class="video-placeholder">
      <el-icon :size="64"><VideoPlay /></el-icon>
      <p>视频加载中...</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { VideoPlay } from '@element-plus/icons-vue'

defineProps<{
  videoUrl: string | null
  subtitleUrl?: string | null
}>()

const videoRef = ref<HTMLVideoElement | null>(null)

const handleLoadedMetadata = () => {
  // 视频元数据加载完成
  if (videoRef.value) {
    console.log('视频时长:', videoRef.value.duration)
  }
}

watch(() => videoRef.value, (newVal) => {
  if (newVal) {
    // 可以在这里添加播放器初始化逻辑
  }
})
</script>

<style lang="scss" scoped>
.video-player-core {
  width: 100%;
  height: 100%;
  background: #000;
  display: flex;
  align-items: center;
  justify-content: center;

  .video-element {
    width: 100%;
    height: 100%;
    outline: none;
  }

  .video-placeholder {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    color: #fff;
    gap: var(--spacing-md);

    p {
      margin: 0;
      font-size: var(--font-size-base);
    }
  }
}
</style>

