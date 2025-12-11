<template>
  <div class="video-player-core">
    <video
      v-if="videoUrl"
      ref="videoRef"
      class="video-element"
      controls
      :src="videoUrl"
      @loadedmetadata="handleLoadedMetadata"
      @timeupdate="handleTimeUpdate"
      @play="emit('play')"
      @pause="emit('pause')"
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
import { ref } from 'vue'
import { VideoPlay } from '@element-plus/icons-vue'

const props = defineProps<{
  videoUrl: string | null
  subtitleUrl?: string | null
}>()

const emit = defineEmits<{
  (e: 'ready', duration: number): void
  (e: 'timeupdate', current: number): void
  (e: 'play'): void
  (e: 'pause'): void
}>()

const videoRef = ref<HTMLVideoElement | null>(null)

const handleLoadedMetadata = () => {
  if (videoRef.value) {
    emit('ready', videoRef.value.duration)
  }
}

const handleTimeUpdate = () => {
  if (videoRef.value) {
    emit('timeupdate', videoRef.value.currentTime)
  }
}

const getCurrentTime = () => videoRef.value?.currentTime || 0
const seek = (time: number) => {
  if (videoRef.value) {
    videoRef.value.currentTime = time
  }
}
const play = () => videoRef.value?.play()
const pause = () => videoRef.value?.pause()

defineExpose({
  getCurrentTime,
  seek,
  play,
  pause,
  videoEl: videoRef
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

