<template>
  <div 
    ref="playerContainerRef"
    class="bili-video-player"
    @click="handlePlayerClick"
    @mousemove="handleMouseMove"
    @mouseleave="handleMouseLeave"
  >
    <!-- 视频元素（隐藏原生控制栏） -->
    <video
      v-if="videoUrl"
      ref="videoRef"
      class="video-element"
      @loadedmetadata="handleLoadedMetadata"
      @timeupdate="handleTimeUpdate"
      @play="handlePlay"
      @pause="handlePause"
      @ended="handlePause"
      @click.stop
    >
      <!-- 原生字幕轨道（用于 SRT/VTT 格式） -->
      <track
        v-if="subtitleUrl && !isJsonSubtitle && subtitleVisible"
        kind="subtitles"
        :src="subtitleUrl"
        label="中文字幕"
        srclang="zh"
        default
      />
      您的浏览器不支持视频播放。
    </video>
    
    <!-- 自定义字幕显示（用于 JSON 格式） -->
    <div 
      v-if="subtitleUrl && isJsonSubtitle && subtitleVisible && currentSubtitleText"
      class="custom-subtitle"
    >
      {{ currentSubtitleText }}
    </div>
    
    <!-- 加载占位符 -->
    <div v-else class="video-placeholder">
      <el-icon :size="64"><VideoPlay /></el-icon>
      <p>视频加载中...</p>
    </div>

    <!-- 自定义控制栏 -->
    <div 
      v-if="videoUrl"
      class="control-bar"
      :class="{ 'is-visible': showControls }"
      @click.stop
    >
      <!-- 进度条 -->
      <div 
        class="progress-bar-wrapper"
        @mouseenter="isProgressHover = true"
        @mouseleave="isProgressHover = false"
        @click="handleProgressClick"
        @mousemove="handleProgressHover"
      >
        <div class="progress-bar-bg">
          <div 
            class="progress-bar-filled"
            :style="{ width: `${progressPercent}%` }"
          ></div>
          <div 
            class="progress-bar-handle"
            :class="{ 'is-visible': isProgressHover || isDragging }"
            :style="{ left: `${progressPercent}%` }"
            @mousedown.stop="startDrag"
          ></div>
        </div>
        <!-- 预览时间提示 -->
        <div 
          v-if="previewTime > 0 && isProgressHover"
          class="progress-preview"
          :style="{ left: `${previewPercent}%` }"
        >
          {{ formatTime(previewTime) }}
        </div>
      </div>

      <!-- 控制按钮区 -->
      <div class="control-buttons">
        <!-- 左侧控制区 -->
        <div class="control-left">
          <!-- 播放/暂停按钮 -->
          <button 
            class="control-btn"
            @click="togglePlayPause"
          >
            <el-icon :size="20">
              <VideoPlay v-if="!isPlaying" />
              <VideoPause v-else />
            </el-icon>
          </button>

          <!-- 时间显示 -->
          <span class="time-display">
            {{ formatTime(currentTime) }} / {{ formatTime(duration) }}
          </span>
        </div>

        <!-- 右侧控制区 -->
        <div class="control-right">
          <!-- 清晰度选择 -->
          <div 
            class="control-item quality-selector"
            @mouseenter="handleQualityMenuEnter"
            @mouseleave="handleQualityMenuLeave"
          >
            <button class="control-btn">
              {{ currentQualityText }}
              <el-icon :size="14" class="arrow-icon">
                <ArrowUp v-if="showQualityMenu" />
                <ArrowDown v-else />
              </el-icon>
            </button>
            <!-- 清晰度菜单 -->
            <div 
              v-show="showQualityMenu"
              class="quality-menu"
              @mouseenter="handleQualityMenuEnter"
              @mouseleave="handleQualityMenuLeave"
            >
              <div
                v-for="quality in availableQualities"
                :key="quality.value"
                class="quality-item"
                :class="{ 'is-active': currentQuality === quality.value }"
                @mousedown.stop="selectQuality(quality.value)"
              >
                {{ quality.label }}
              </div>
            </div>
          </div>

          <!-- 倍速选择 -->
          <div 
            class="control-item speed-selector"
            @mouseenter="handleSpeedMenuEnter"
            @mouseleave="handleSpeedMenuLeave"
          >
            <button class="control-btn">
              {{ currentSpeedText }}
              <el-icon :size="14" class="arrow-icon">
                <ArrowUp v-if="showSpeedMenu" />
                <ArrowDown v-else />
              </el-icon>
            </button>
            <!-- 倍速菜单 -->
            <div 
              v-show="showSpeedMenu"
              class="speed-menu"
              @mouseenter="handleSpeedMenuEnter"
              @mouseleave="handleSpeedMenuLeave"
            >
              <div
                v-for="speed in speedOptions"
                :key="speed"
                class="speed-item"
                :class="{ 'is-active': playbackRate === speed }"
                @mousedown.stop="selectSpeed(speed)"
              >
                {{ speed }}x
              </div>
            </div>
          </div>

          <!-- 音量控制 -->
          <div 
            class="control-item volume-control"
            @mouseenter="handleVolumeSliderEnter"
            @mouseleave="handleVolumeSliderLeave"
          >
            <button class="control-btn" @mousedown.stop="toggleMute">
              <!-- 静音图标 -->
              <svg 
                v-if="isMuted || volume === 0"
                class="volume-icon"
                viewBox="0 0 24 24"
                fill="currentColor"
                width="20"
                height="20"
              >
                <path d="M16.5 12c0-1.77-1.02-3.29-2.5-4.03v2.21l2.45 2.45c.03-.2.05-.41.05-.63zm2.5 0c0 .94-.2 1.82-.54 2.64l1.51 1.51C20.63 14.91 21 13.5 21 12c0-4.28-2.99-7.86-7-8.77v2.06c2.89.86 5 3.54 5 6.71zM4.27 3L3 4.27 7.73 9H3v6h4l5 5v-6.73l4.25 4.25c-.67.52-1.42.93-2.25 1.18v2.06c1.38-.31 2.63-.95 3.69-1.81L19.73 21 21 19.73l-9-9L4.27 3zM12 4L9.91 6.09 12 8.18V4z"/>
              </svg>
              <!-- 音量图标 -->
              <svg 
                v-else
                class="volume-icon"
                viewBox="0 0 24 24"
                fill="currentColor"
                width="20"
                height="20"
              >
                <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/>
              </svg>
            </button>
            <!-- 音量滑块 -->
            <div 
              v-show="showVolumeSlider"
              class="volume-slider-wrapper"
              @mouseenter="handleVolumeSliderEnter"
              @mouseleave="handleVolumeSliderLeave"
            >
              <div 
                class="volume-slider"
                @mousedown.stop="handleVolumeClick"
              >
                <div class="volume-slider-bg">
                  <div 
                    class="volume-slider-filled"
                    :style="{ height: `${volume * 100}%` }"
                  ></div>
                  <div 
                    class="volume-slider-handle"
                    :style="{ bottom: `${volume * 100}%` }"
                  ></div>
                </div>
              </div>
            </div>
          </div>

          <!-- 字幕开关 -->
          <button 
            v-if="subtitleUrl"
            class="control-btn"
            @click="toggleSubtitle"
            :title="subtitleVisible ? '隐藏字幕' : '显示字幕'"
          >
            <svg 
              class="subtitle-icon"
              viewBox="0 0 24 24"
              fill="currentColor"
              width="20"
              height="20"
            >
              <path v-if="subtitleVisible" d="M19 4H5c-1.11 0-2 .9-2 2v12c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 14H5V6h14v12zM7 15h10v2H7zm0-4h10v2H7zm0-4h7v2H7z"/>
              <path v-else d="M19 4H5c-1.11 0-2 .9-2 2v12c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 14H5V6h14v12zM7 15h10v2H7zm0-4h10v2H7zm0-4h7v2H7z" opacity="0.3"/>
            </svg>
          </button>

          <!-- 全屏按钮 -->
          <button 
            class="control-btn"
            @click="toggleFullscreen"
          >
            <!-- 全屏图标 -->
            <svg 
              v-if="!isFullscreen"
              class="fullscreen-icon"
              viewBox="0 0 24 24"
              fill="currentColor"
              width="20"
              height="20"
            >
              <path d="M7 14H5v5h5v-2H7v-3zm-2-4h2V7h3V5H5v5zm12 7h-3v2h5v-5h-2v3zM14 5v2h3v3h2V5h-5z"/>
            </svg>
            <!-- 退出全屏图标 -->
            <svg 
              v-else
              class="fullscreen-icon"
              viewBox="0 0 24 24"
              fill="currentColor"
              width="20"
              height="20"
            >
              <path d="M5 16h3v3h2v-5H5v2zm3-8H5v2h5V5H8v3zm6 11h2v-3h3v-2h-5v5zm2-11V5h-2v5h5V8h-3z"/>
            </svg>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from "vue";
import { 
  VideoPlay, 
  VideoPause, 
  ArrowUp, 
  ArrowDown
} from "@element-plus/icons-vue";
import Hls from "hls.js";
import { resolveFileUrl } from "@/shared/utils/urlHelpers";

const props = defineProps<{
  videoUrl?: string | null;
  subtitleUrl?: string | null;
}>();

const emit = defineEmits<{
  (e: "ready", duration: number): void;
  (e: "timeupdate", current: number): void;
  (e: "play"): void;
  (e: "pause"): void;
}>();

// Refs
const playerContainerRef = ref<HTMLDivElement | null>(null);
const videoRef = ref<HTMLVideoElement | null>(null);
const hlsRef = ref<Hls | null>(null);

// 播放状态
const isPlaying = ref(false);
const currentTime = ref(0);
const duration = ref(0);
const volume = ref(1);
const isMuted = ref(false);
const playbackRate = ref(1);

// 控制栏显示
const showControls = ref(true);
const controlsTimer = ref<number | null>(null);
const hideControlsDelay = 3000; // 3秒后隐藏控制栏

// 进度条状态
const isProgressHover = ref(false);
const isDragging = ref(false);
const previewTime = ref(0);
const previewPercent = ref(0);

// 菜单显示状态
const showQualityMenu = ref(false);
const showSpeedMenu = ref(false);
const showVolumeSlider = ref(false);

// 字幕状态
const subtitleVisible = ref(true); // 默认显示字幕
const isJsonSubtitle = ref(false); // 是否为 JSON 格式字幕
const subtitleData = ref<Array<{ start_time: number; end_time: number; text: string }>>([]);
const currentSubtitleText = ref('');

// 清晰度选项（从 master.m3u8 解析）
const qualityOptions = ref([
  { value: "1080p", label: "1080P 高清" },
  { value: "720p", label: "720P 高清" },
  { value: "480p", label: "480P 清晰" },
  { value: "360p", label: "360P 流畅" },
]);

const currentQuality = ref("1080p");
const availableQualities = computed(() => {
  // 如果视频 URL 是 master.m3u8，显示所有选项
  // 否则只显示当前清晰度
  if (props.videoUrl && props.videoUrl.includes('master.m3u8')) {
    return qualityOptions.value;
  }
  return qualityOptions.value.filter(q => q.value === currentQuality.value);
});

const currentQualityText = computed(() => {
  const option = qualityOptions.value.find(q => q.value === currentQuality.value);
  return option?.label || "1080P 高清";
});

// 解析 master.m3u8 获取可用清晰度
const parseMasterPlaylist = async (url: string) => {
  try {
    const response = await fetch(url);
    const text = await response.text();
    const lines = text.split('\n');
    
    const qualities: Array<{ value: string; label: string; url: string }> = [];
    let currentResolution = '';
    let currentBandwidth = 0;
    
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim();
      
      // 解析 #EXT-X-STREAM-INF 行
      if (line.startsWith('#EXT-X-STREAM-INF')) {
        const resolutionMatch = line.match(/RESOLUTION=(\d+)x(\d+)/);
        const bandwidthMatch = line.match(/BANDWIDTH=(\d+)/);
        
        if (resolutionMatch) {
          const width = parseInt(resolutionMatch[1]);
          const height = parseInt(resolutionMatch[2]);
          currentResolution = `${height}p`;
          currentBandwidth = bandwidthMatch ? parseInt(bandwidthMatch[1]) : 0;
        }
      }
      // 解析实际的播放列表 URL
      else if (line && !line.startsWith('#') && currentResolution) {
        // 构建完整的 URL
        const baseUrl = url.substring(0, url.lastIndexOf('/'));
        const qualityUrl = line.startsWith('http') ? line : `${baseUrl}/${line}`;
        
        // 确定清晰度标签
        let label = '';
        if (currentResolution === '1080p') label = '1080P 高清';
        else if (currentResolution === '720p') label = '720P 高清';
        else if (currentResolution === '480p') label = '480P 清晰';
        else if (currentResolution === '360p') label = '360P 流畅';
        else label = `${currentResolution} 清晰`;
        
        qualities.push({
          value: currentResolution,
          label,
          url: qualityUrl
        });
        
        currentResolution = '';
      }
    }
    
    if (qualities.length > 0) {
      qualityOptions.value = qualities.map(q => ({ value: q.value, label: q.label }));
      // 默认选择最高清晰度
      currentQuality.value = qualities[0].value;
    }
    
    return qualities;
  } catch (error) {
    console.error('解析 master.m3u8 失败:', error);
    return [];
  }
};

// 倍速选项
const speedOptions = [2.0, 1.5, 1.25, 1.0, 0.75];

const currentSpeedText = computed(() => {
  return `${playbackRate.value}x`;
});

// 全屏状态
const isFullscreen = ref(false);

// 计算属性
const progressPercent = computed(() => {
  if (duration.value === 0) return 0;
  return (currentTime.value / duration.value) * 100;
});

// 格式化时间
const formatTime = (seconds: number): string => {
  if (!isFinite(seconds) || isNaN(seconds)) return "00:00";
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  
  if (h > 0) {
    return `${h.toString().padStart(2, "0")}:${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  }
  return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
};

// 初始化 HLS 播放器
const initHlsPlayer = (url: string) => {
  if (!videoRef.value) return;
  
  // 检查浏览器是否原生支持 HLS
  if (videoRef.value.canPlayType('application/vnd.apple.mpegurl')) {
    // Safari 原生支持，直接使用
    videoRef.value.src = url;
    return;
  }
  
  // 其他浏览器使用 hls.js
  if (Hls.isSupported()) {
    if (hlsRef.value) {
      hlsRef.value.destroy();
    }
    
    const hls = new Hls({
      enableWorker: true,
      lowLatencyMode: false,
      backBufferLength: 90
    });
    
    hls.loadSource(url);
    hls.attachMedia(videoRef.value);
    
    // 监听清晰度变化
    hls.on(Hls.Events.MANIFEST_PARSED, () => {
      console.log('HLS manifest 解析完成，可用清晰度:', hls.levels.map(l => `${l.height}p`));
    });
    
    hlsRef.value = hls;
  } else {
    console.error('浏览器不支持 HLS 播放');
  }
};

// 视频事件处理
const handleLoadedMetadata = () => {
  if (videoRef.value) {
    duration.value = videoRef.value.duration;
    volume.value = videoRef.value.volume;
    isMuted.value = videoRef.value.muted;
    playbackRate.value = videoRef.value.playbackRate;
    emit("ready", videoRef.value.duration);
  }
};

const handleTimeUpdate = () => {
  if (videoRef.value && !isDragging.value) {
    currentTime.value = videoRef.value.currentTime;
    emit("timeupdate", videoRef.value.currentTime);
    
    // 更新 JSON 字幕显示
    if (isJsonSubtitle.value && subtitleVisible.value) {
      updateSubtitleDisplay(currentTime.value);
    }
  }
};

const handlePlay = () => {
  isPlaying.value = true;
  emit("play");
};

const handlePause = () => {
  isPlaying.value = false;
  emit("pause");
};

// 播放/暂停切换
const togglePlayPause = () => {
  if (videoRef.value) {
    if (isPlaying.value) {
      videoRef.value.pause();
    } else {
      videoRef.value.play();
    }
  }
};

// 点击播放器区域切换播放/暂停
const handlePlayerClick = (e: MouseEvent) => {
  // 如果点击的是控制栏区域，不切换播放状态
  const target = e.target as HTMLElement;
  if (target.closest('.control-bar')) {
    return;
  }
  togglePlayPause();
};

// 控制栏显示/隐藏
const showControlsBar = () => {
  showControls.value = true;
  if (controlsTimer.value) {
    clearTimeout(controlsTimer.value);
  }
  if (isPlaying.value) {
    controlsTimer.value = window.setTimeout(() => {
      if (isPlaying.value && !isProgressHover.value && !showQualityMenu.value && !showSpeedMenu.value && !showVolumeSlider.value) {
        showControls.value = false;
      }
    }, hideControlsDelay);
  }
};

const handleMouseMove = () => {
  showControlsBar();
};

const handleMouseLeave = () => {
  if (isPlaying.value && !isProgressHover.value) {
    if (controlsTimer.value) {
      clearTimeout(controlsTimer.value);
    }
    controlsTimer.value = window.setTimeout(() => {
      showControls.value = false;
    }, hideControlsDelay);
  }
};

// 进度条处理
const handleProgressClick = (e: MouseEvent) => {
  if (!videoRef.value || duration.value === 0) return;
  const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
  const percent = (e.clientX - rect.left) / rect.width;
  const newTime = Math.max(0, Math.min(duration.value, percent * duration.value));
  seek(newTime);
};

const handleProgressHover = (e: MouseEvent) => {
  if (!videoRef.value || duration.value === 0) return;
  const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
  const percent = Math.max(0, Math.min(100, ((e.clientX - rect.left) / rect.width) * 100));
  previewPercent.value = percent;
  previewTime.value = (percent / 100) * duration.value;
};

const startDrag = (e: MouseEvent) => {
  if (!videoRef.value || duration.value === 0) return;
  e.preventDefault();
  isDragging.value = true;
  showControls.value = true;

  const handleMouseMove = (moveEvent: MouseEvent) => {
    if (!playerContainerRef.value) return;
    const rect = playerContainerRef.value.getBoundingClientRect();
    const percent = Math.max(0, Math.min(100, ((moveEvent.clientX - rect.left) / rect.width) * 100));
    const newTime = (percent / 100) * duration.value;
    currentTime.value = newTime;
    previewTime.value = newTime;
    previewPercent.value = percent;
  };

  const handleMouseUp = () => {
    if (videoRef.value && isDragging.value) {
      videoRef.value.currentTime = currentTime.value;
      emit("timeupdate", currentTime.value);
    }
    isDragging.value = false;
    document.removeEventListener("mousemove", handleMouseMove);
    document.removeEventListener("mouseup", handleMouseUp);
  };

  document.addEventListener("mousemove", handleMouseMove);
  document.addEventListener("mouseup", handleMouseUp);
};

// 清晰度选择
const qualityUrlMap = ref<Map<string, string>>(new Map());

const selectQuality = async (quality: string) => {
  if (currentQuality.value === quality) {
    showQualityMenu.value = false;
    return;
  }
  
  // 如果视频 URL 是 master.m3u8，需要切换到对应的清晰度流
  if (props.videoUrl && props.videoUrl.includes('master.m3u8')) {
    const qualityUrl = qualityUrlMap.value.get(quality);
    if (qualityUrl && videoRef.value) {
      const currentTime = videoRef.value.currentTime;
      const wasPlaying = !videoRef.value.paused;
      
      // 如果使用 hls.js，通过 level 切换
      if (hlsRef.value) {
        const levelIndex = hlsRef.value.levels.findIndex(level => {
          const levelQuality = `${level.height}p`;
          return levelQuality === quality;
        });
        
        if (levelIndex !== -1) {
          hlsRef.value.currentLevel = levelIndex;
          currentQuality.value = quality;
          showQualityMenu.value = false;
          return;
        }
      }
      
      // 否则直接切换视频源
      if (videoRef.value.canPlayType('application/vnd.apple.mpegurl')) {
        // Safari 原生支持
        videoRef.value.src = qualityUrl;
        videoRef.value.load();
      } else {
        // 使用 hls.js 重新加载
        initHlsPlayer(qualityUrl);
      }
      
      // 恢复播放状态
      if (wasPlaying) {
        videoRef.value.play().then(() => {
          videoRef.value!.currentTime = currentTime;
        }).catch(err => {
          console.error('切换清晰度后播放失败:', err);
        });
      } else {
        videoRef.value.currentTime = currentTime;
      }
    }
  }
  
  currentQuality.value = quality;
  showQualityMenu.value = false;
};

// 菜单进入/离开处理（延迟关闭，允许点击）
const qualityMenuLeaveTimer = ref<number | null>(null);
const handleQualityMenuEnter = () => {
  // 清除关闭定时器
  if (qualityMenuLeaveTimer.value) {
    clearTimeout(qualityMenuLeaveTimer.value);
    qualityMenuLeaveTimer.value = null;
  }
  showQualityMenu.value = true;
};

const handleQualityMenuLeave = () => {
  // 延迟关闭，给鼠标移动到菜单上的时间
  if (qualityMenuLeaveTimer.value) {
    clearTimeout(qualityMenuLeaveTimer.value);
  }
  qualityMenuLeaveTimer.value = window.setTimeout(() => {
    showQualityMenu.value = false;
    qualityMenuLeaveTimer.value = null;
  }, 300); // 300ms 延迟，允许鼠标移动到菜单上
};

const speedMenuLeaveTimer = ref<number | null>(null);
const handleSpeedMenuEnter = () => {
  if (speedMenuLeaveTimer.value) {
    clearTimeout(speedMenuLeaveTimer.value);
    speedMenuLeaveTimer.value = null;
  }
  showSpeedMenu.value = true;
};

const handleSpeedMenuLeave = () => {
  if (speedMenuLeaveTimer.value) {
    clearTimeout(speedMenuLeaveTimer.value);
  }
  speedMenuLeaveTimer.value = window.setTimeout(() => {
    showSpeedMenu.value = false;
    speedMenuLeaveTimer.value = null;
  }, 300);
};

const volumeSliderLeaveTimer = ref<number | null>(null);
const handleVolumeSliderEnter = () => {
  if (volumeSliderLeaveTimer.value) {
    clearTimeout(volumeSliderLeaveTimer.value);
    volumeSliderLeaveTimer.value = null;
  }
  showVolumeSlider.value = true;
};

const handleVolumeSliderLeave = () => {
  if (volumeSliderLeaveTimer.value) {
    clearTimeout(volumeSliderLeaveTimer.value);
  }
  volumeSliderLeaveTimer.value = window.setTimeout(() => {
    showVolumeSlider.value = false;
    volumeSliderLeaveTimer.value = null;
  }, 300);
};

// 倍速选择
const selectSpeed = (speed: number) => {
  if (videoRef.value) {
    playbackRate.value = speed;
    videoRef.value.playbackRate = speed;
  }
  showSpeedMenu.value = false;
};

// 音量控制
const toggleMute = () => {
  if (videoRef.value) {
    isMuted.value = !isMuted.value;
    videoRef.value.muted = isMuted.value;
  }
};

const handleVolumeClick = (e: MouseEvent) => {
  if (!videoRef.value) return;
  e.preventDefault();
  e.stopPropagation();
  
  const slider = e.currentTarget as HTMLElement;
  const rect = slider.getBoundingClientRect();
  const percent = 1 - ((e.clientY - rect.top) / rect.height);
  const newVolume = Math.max(0, Math.min(1, percent));
  volume.value = newVolume;
  videoRef.value.volume = newVolume;
  if (newVolume > 0) {
    isMuted.value = false;
    videoRef.value.muted = false;
  }
};

// 全屏控制
const toggleFullscreen = () => {
  if (!playerContainerRef.value) return;

  if (!isFullscreen.value) {
    // 进入全屏
    if (playerContainerRef.value.requestFullscreen) {
      playerContainerRef.value.requestFullscreen();
    } else if ((playerContainerRef.value as any).webkitRequestFullscreen) {
      (playerContainerRef.value as any).webkitRequestFullscreen();
    } else if ((playerContainerRef.value as any).mozRequestFullScreen) {
      (playerContainerRef.value as any).mozRequestFullScreen();
    } else if ((playerContainerRef.value as any).msRequestFullscreen) {
      (playerContainerRef.value as any).msRequestFullscreen();
    }
  } else {
    // 退出全屏
    if (document.exitFullscreen) {
      document.exitFullscreen();
    } else if ((document as any).webkitExitFullscreen) {
      (document as any).webkitExitFullscreen();
    } else if ((document as any).mozCancelFullScreen) {
      (document as any).mozCancelFullScreen();
    } else if ((document as any).msExitFullscreen) {
      (document as any).msExitFullscreen();
    }
  }
};

// 字幕控制
const toggleSubtitle = () => {
  subtitleVisible.value = !subtitleVisible.value;
  if (!subtitleVisible.value) {
    currentSubtitleText.value = '';
  } else if (isJsonSubtitle.value && videoRef.value) {
    updateSubtitleDisplay(videoRef.value.currentTime);
  }
};

// 加载字幕文件
const loadSubtitle = async (url: string) => {
  try {
    // 解析 URL（支持相对路径）
    const fullUrl = resolveFileUrl(url);
    
    // 判断是否为 JSON 格式
    if (url.toLowerCase().endsWith('.json')) {
      isJsonSubtitle.value = true;
      const response = await fetch(fullUrl);
      if (!response.ok) {
        throw new Error(`加载字幕失败: ${response.statusText}`);
      }
      const data = await response.json();
      subtitleData.value = parseJsonSubtitle(data);
    } else {
      isJsonSubtitle.value = false;
      subtitleData.value = [];
    }
  } catch (error) {
    console.error('加载字幕失败:', error);
    isJsonSubtitle.value = false;
    subtitleData.value = [];
  }
};

// 解析 JSON 字幕（支持 bilibili-evolved 格式）
const parseJsonSubtitle = (data: any): Array<{ start_time: number; end_time: number; text: string }> => {
  const subtitles: Array<{ start_time: number; end_time: number; text: string }> = [];
  
  // bilibili-evolved 格式：{ "body": [...] }
  if (data && typeof data === 'object' && 'body' in data && Array.isArray(data.body)) {
    data.body.forEach((item: any) => {
      const from = item.from ?? item.start ?? item.start_time ?? 0;
      const to = item.to ?? item.end ?? item.end_time ?? 0;
      const content = item.content ?? item.text ?? '';
      if (content) {
        subtitles.push({
          start_time: Number(from),
          end_time: Number(to),
          text: String(content).trim()
        });
      }
    });
  }
  // 标准数组格式
  else if (Array.isArray(data)) {
    data.forEach((item: any) => {
      if (item && typeof item === 'object') {
        const start = item.start ?? item.start_time ?? item.from ?? 0;
        const end = item.end ?? item.end_time ?? item.to ?? 0;
        const text = item.text ?? item.content ?? '';
        if (text) {
          subtitles.push({
            start_time: Number(start),
            end_time: Number(end),
            text: String(text).trim()
          });
        }
      }
    });
  }
  // 嵌套格式：{ "subtitles": [...] }
  else if (data && typeof data === 'object' && 'subtitles' in data && Array.isArray(data.subtitles)) {
    data.subtitles.forEach((item: any) => {
      const start = item.start ?? item.start_time ?? item.from ?? 0;
      const end = item.end ?? item.end_time ?? item.to ?? 0;
      const text = item.text ?? item.content ?? '';
      if (text) {
        subtitles.push({
          start_time: Number(start),
          end_time: Number(end),
          text: String(text).trim()
        });
      }
    });
  }
  
  // 按开始时间排序
  subtitles.sort((a, b) => a.start_time - b.start_time);
  return subtitles;
};

// 根据当前播放时间更新字幕显示
const updateSubtitleDisplay = (currentTime: number) => {
  if (!subtitleData.value || subtitleData.value.length === 0) {
    currentSubtitleText.value = '';
    return;
  }
  
  // 查找当前时间对应的字幕
  const subtitle = subtitleData.value.find(
    item => currentTime >= item.start_time && currentTime <= item.end_time
  );
  
  currentSubtitleText.value = subtitle ? subtitle.text : '';
};

// 监听全屏状态变化
const handleFullscreenChange = () => {
  isFullscreen.value = !!(
    document.fullscreenElement ||
    (document as any).webkitFullscreenElement ||
    (document as any).mozFullScreenElement ||
    (document as any).msFullscreenElement
  );
};

// Seek 方法（供外部调用）
const seek = (time: number) => {
  if (videoRef.value) {
    videoRef.value.currentTime = time;
    currentTime.value = time;
    emit("timeupdate", time);
  }
};

const getCurrentTime = () => videoRef.value?.currentTime || 0;
const play = () => {
  videoRef.value?.play();
};
const pause = () => {
  videoRef.value?.pause();
};

// 生命周期
onMounted(() => {
  document.addEventListener("fullscreenchange", handleFullscreenChange);
  document.addEventListener("webkitfullscreenchange", handleFullscreenChange);
  document.addEventListener("mozfullscreenchange", handleFullscreenChange);
  document.addEventListener("MSFullscreenChange", handleFullscreenChange);
});

onUnmounted(() => {
  if (controlsTimer.value) {
    clearTimeout(controlsTimer.value);
  }
  if (qualityMenuLeaveTimer.value) {
    clearTimeout(qualityMenuLeaveTimer.value);
  }
  if (speedMenuLeaveTimer.value) {
    clearTimeout(speedMenuLeaveTimer.value);
  }
  if (volumeSliderLeaveTimer.value) {
    clearTimeout(volumeSliderLeaveTimer.value);
  }
  // 清理 HLS 实例
  if (hlsRef.value) {
    hlsRef.value.destroy();
    hlsRef.value = null;
  }
  document.removeEventListener("fullscreenchange", handleFullscreenChange);
  document.removeEventListener("webkitfullscreenchange", handleFullscreenChange);
  document.removeEventListener("mozfullscreenchange", handleFullscreenChange);
  document.removeEventListener("MSFullscreenChange", handleFullscreenChange);
});

// 监听字幕 URL 变化，加载字幕
watch(() => props.subtitleUrl, async (newUrl) => {
  if (newUrl) {
    await loadSubtitle(newUrl);
  } else {
    isJsonSubtitle.value = false;
    subtitleData.value = [];
    currentSubtitleText.value = '';
  }
}, { immediate: true });

// 监听视频 URL 变化，重置状态并解析清晰度
watch(() => props.videoUrl, async (newUrl) => {
  if (!newUrl) return;
  
  // 等待 video 元素挂载
  await nextTick();
  
  if (!videoRef.value) return;
  
  // 清理旧的 HLS 实例
  if (hlsRef.value) {
    hlsRef.value.destroy();
    hlsRef.value = null;
  }
  
  currentTime.value = 0;
  duration.value = 0;
  isPlaying.value = false;
  
  // 如果 URL 是 master.m3u8，解析可用清晰度
  if (newUrl.includes('master.m3u8')) {
    const qualities = await parseMasterPlaylist(newUrl);
    // 构建清晰度 URL 映射
    qualityUrlMap.value.clear();
    qualities.forEach(q => {
      qualityUrlMap.value.set(q.value, q.url);
    });
    
    // 默认选择最高清晰度
    if (qualities.length > 0) {
      currentQuality.value = qualities[0].value;
      // 初始化 HLS 播放器
      initHlsPlayer(qualities[0].url);
    }
  } else if (newUrl.includes('.m3u8')) {
    // 单个清晰度的 HLS 流
    initHlsPlayer(newUrl);
  } else {
    // 非 HLS 视频（MP4 等），直接设置 src
    videoRef.value.src = newUrl;
    // 非 HLS 视频，重置清晰度选项
    qualityOptions.value = [
      { value: "1080p", label: "1080P 高清" },
      { value: "720p", label: "720P 高清" },
      { value: "480p", label: "480P 清晰" },
      { value: "360p", label: "360P 流畅" },
    ];
    currentQuality.value = "1080p";
  }
}, { immediate: true });

defineExpose({
  getCurrentTime,
  seek,
  play,
  pause,
  videoEl: videoRef,
});
</script>

<style lang="scss" scoped>
.bili-video-player {
  position: relative;
  width: 100%;
  height: 100%;
  background: #000;
  overflow: hidden;
  cursor: none;
  user-select: none;

  &:hover {
    cursor: default;
  }

  &:hover .control-bar {
    opacity: 1;
    pointer-events: auto;
  }

  .video-element {
    width: 100%;
    height: 100%;
    outline: none;
    display: block;
  }

  .video-placeholder {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    color: #fff;
    gap: 12px;
    height: 100%;

    p {
      margin: 0;
      font-size: 14px;
    }
  }

  // 自定义字幕显示
  .custom-subtitle {
    position: absolute;
    bottom: 80px;
    left: 50%;
    transform: translateX(-50%);
    padding: 8px 16px;
    background: rgba(0, 0, 0, 0.7);
    color: #fff;
    font-size: 18px;
    line-height: 1.5;
    border-radius: 4px;
    max-width: 80%;
    text-align: center;
    word-wrap: break-word;
    pointer-events: none;
    z-index: 10;
    transition: opacity 0.3s ease;
  }

  // 控制栏
  .control-bar {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    padding: 0 16px 12px;
    background: linear-gradient(to top, rgba(0, 0, 0, 0.7), transparent);
    opacity: 0;
    transition: opacity 0.3s ease;
    pointer-events: none;

    &.is-visible {
      opacity: 1;
      pointer-events: auto;
    }

    // 进度条
    .progress-bar-wrapper {
      position: relative;
      height: 5px;
      margin-bottom: 12px;
      cursor: pointer;

      .progress-bar-bg {
        position: relative;
        width: 100%;
        height: 3px;
        background: rgba(255, 255, 255, 0.3);
        border-radius: 2px;
        transition: height 0.2s;

        .progress-bar-filled {
          position: absolute;
          top: 0;
          left: 0;
          height: 100%;
          background: var(--primary-color);
          border-radius: 2px;
          transition: width 0.1s;
        }

        .progress-bar-handle {
          position: absolute;
          top: 50%;
          left: 0;
          width: 12px;
          height: 12px;
          background: var(--primary-color);
          border: 2px solid #fff;
          border-radius: 50%;
          transform: translate(-50%, -50%);
          opacity: 0;
          transition: opacity 0.2s;
          cursor: grab;

          &:active {
            cursor: grabbing;
          }

          &.is-visible {
            opacity: 1;
          }
        }
      }

      &:hover .progress-bar-bg {
        height: 5px;

        .progress-bar-handle {
          opacity: 1;
        }
      }

      .progress-preview {
        position: absolute;
        bottom: 100%;
        margin-bottom: 8px;
        transform: translateX(-50%);
        background: rgba(0, 0, 0, 0.9);
        color: #fff;
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 12px;
        white-space: nowrap;
        pointer-events: none;
        z-index: 1001;
      }
    }

    // 控制按钮区
    .control-buttons {
      display: flex;
      align-items: center;
      justify-content: space-between;
      height: 40px;

      .control-left {
        display: flex;
        align-items: center;
        gap: 16px;
      }

      .control-right {
        display: flex;
        align-items: center;
        gap: 8px;
      }

      .control-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 36px;
        height: 36px;
        background: transparent;
        border: none;
        color: #fff;
        cursor: pointer;
        border-radius: 4px;
        transition: all 0.2s;

        &:hover {
          background: rgba(255, 255, 255, 0.1);
          color: var(--primary-color);
        }

        .el-icon {
          color: inherit;
        }

        .volume-icon,
        .fullscreen-icon {
          color: inherit;
          transition: color 0.2s;
        }
      }

      .time-display {
        color: #fff;
        font-size: 13px;
        font-weight: 500;
        user-select: none;
      }

      // 控制项（清晰度、倍速、音量）
      .control-item {
        position: relative;

        .arrow-icon {
          margin-left: 4px;
          transition: transform 0.2s;
        }

        // 清晰度菜单
        .quality-menu {
          position: absolute;
          bottom: 100%;
          right: 0;
          margin-bottom: 8px;
          background: rgba(0, 0, 0, 0.95);
          border-radius: 4px;
          min-width: 120px;
          overflow: hidden;
          z-index: 10000;
          pointer-events: auto;
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);

          .quality-item {
            padding: 10px 16px;
            color: #fff;
            font-size: 13px;
            cursor: pointer;
            transition: background 0.15s;
            user-select: none;
            white-space: nowrap;

            &:hover {
              background: rgba(255, 255, 255, 0.15);
            }

            &:active {
              background: rgba(255, 255, 255, 0.2);
            }

            &.is-active {
              color: var(--primary-color);
              background: rgba(250, 114, 152, 0.15);
              font-weight: 500;
            }
          }
        }

        // 倍速菜单
        .speed-menu {
          position: absolute;
          bottom: 100%;
          right: 0;
          margin-bottom: 8px;
          background: rgba(0, 0, 0, 0.95);
          border-radius: 4px;
          min-width: 80px;
          overflow: hidden;
          z-index: 10000;
          pointer-events: auto;
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);

          .speed-item {
            padding: 10px 16px;
            color: #fff;
            font-size: 13px;
            cursor: pointer;
            transition: background 0.15s;
            user-select: none;
            white-space: nowrap;

            &:hover {
              background: rgba(255, 255, 255, 0.15);
            }

            &:active {
              background: rgba(255, 255, 255, 0.2);
            }

            &.is-active {
              color: var(--primary-color);
              background: rgba(250, 114, 152, 0.15);
              font-weight: 500;
            }
          }
        }

        // 音量滑块
        .volume-slider-wrapper {
          position: absolute;
          bottom: 100%;
          right: 0;
          margin-bottom: 8px;
          padding: 8px 0;
          z-index: 10000;
          pointer-events: auto;
        }

        .volume-slider {
          width: 32px;
          height: 100px;
          background: rgba(0, 0, 0, 0.95);
          border-radius: 4px;
          padding: 8px;
          cursor: pointer;
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        }

        .volume-slider-bg {
          position: relative;
          width: 4px;
          height: 100%;
          background: rgba(255, 255, 255, 0.3);
          border-radius: 2px;
          margin: 0 auto;
        }

        .volume-slider-filled {
          position: absolute;
          bottom: 0;
          left: 0;
          width: 100%;
          background: var(--primary-color);
          border-radius: 2px;
          transition: height 0.1s;
        }

        .volume-slider-handle {
          position: absolute;
          left: 50%;
          transform: translate(-50%, 50%);
          width: 10px;
          height: 10px;
          background: var(--primary-color);
          border: 2px solid #fff;
          border-radius: 50%;
          pointer-events: none;
        }
      }
    }
  }
}

// 全屏样式
:global(.bili-video-player:fullscreen),
:global(.bili-video-player:-webkit-full-screen),
:global(.bili-video-player:-moz-full-screen),
:global(.bili-video-player:-ms-fullscreen) {
  width: 100vw;
  height: 100vh;
  background: #000;
}
</style>
