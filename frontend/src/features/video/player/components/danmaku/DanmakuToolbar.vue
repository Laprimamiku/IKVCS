<template>
  <div class="bili-danmaku-toolbar">
    <!-- Left Controls -->
    <div class="toolbar-left">
      <div class="view-count" v-if="viewCount !== undefined">
        <el-icon><VideoPlay /></el-icon>
        <span>{{ formatNumber(viewCount) }}</span>
      </div>
      
      <div class="toolbar-divider"></div>
      
      <!-- Danmaku Toggle -->
      <div class="danmaku-toggle" :class="{ active: showDanmaku }" @click="handleToggle(!showDanmaku)">
        <el-icon><ChatDotRound /></el-icon>
        <span>弹幕</span>
        <span class="toggle-status">{{ showDanmaku ? '开' : '关' }}</span>
      </div>
      
      <!-- Quality Filter -->
      <div 
        class="quality-filter" 
        :class="{ active: internalFilterState }" 
        @click="handleFilterChange(!internalFilterState)"
        title="开启后将隐藏AI评分低于60的弹幕"
      >
        <el-icon><Filter /></el-icon>
        <span>{{ internalFilterState ? '精选' : '全部' }}</span>
      </div>
      
      <!-- Danmaku Settings -->
      <el-popover placement="top" :width="280" trigger="click">
        <template #reference>
          <div class="settings-btn">
            <el-icon><Setting /></el-icon>
          </div>
        </template>
        <div class="danmaku-settings">
          <div class="setting-item">
            <span class="setting-label">不透明度</span>
            <el-slider v-model="opacity" :min="10" :max="100" :format-tooltip="(val: number) => `${val}%`" />
          </div>
          <div class="setting-item">
            <span class="setting-label">弹幕速度</span>
            <el-slider v-model="speed" :min="50" :max="200" :format-tooltip="(val: number) => `${val}%`" />
          </div>
          <div class="setting-item">
            <span class="setting-label">字体大小</span>
            <el-slider v-model="fontSize" :min="12" :max="36" :format-tooltip="(val: number) => `${val}px`" />
          </div>
        </div>
      </el-popover>
    </div>

    <!-- Danmaku Input -->
    <div class="toolbar-center">
      <DanmakuInput
        :preset-colors="presetColors"
        :disabled="disabled"
        :on-send="onSend"
      />
    </div>

    <!-- Right Controls -->
    <div class="toolbar-right">
      <div class="send-tip" v-if="disabled">
        <span>登录后发弹幕</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from "vue";
import { VideoPlay, ChatDotRound, Filter, Setting } from "@element-plus/icons-vue";
import DanmakuInput from "./DanmakuInput.vue";
import { formatNumber } from "@/features/video/player/utils/videoFormatters";

const props = defineProps<{
  showDanmaku: boolean;
  filterLowScore?: boolean;
  viewCount?: number;
  presetColors: string[];
  disabled: boolean;
  onSend: (content: string, color: string) => Promise<boolean>;
}>();

const emit = defineEmits<{
  "update:showDanmaku": [value: boolean];
  "update:filterLowScore": [value: boolean];
}>();

// Local state
const internalFilterState = ref(props.filterLowScore || false);
const opacity = ref(100);
const speed = ref(100);
const fontSize = ref(25);

watch(() => props.filterLowScore, (val) => {
  if (val !== undefined) internalFilterState.value = val;
});

const handleToggle = (value: boolean) => {
  emit("update:showDanmaku", value);
};

const handleFilterChange = (value: boolean) => {
  internalFilterState.value = value;
  emit("update:filterLowScore", value);
};
</script>

<style lang="scss" scoped>
.bili-danmaku-toolbar {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  height: 48px;
  padding: 0 var(--space-4);
  background: var(--bg-white);
  border-top: 1px solid var(--divider-color);
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex-shrink: 0;
}

.view-count {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--font-size-sm);
  color: var(--text-tertiary);
  
  .el-icon {
    font-size: 14px;
  }
}

.toolbar-divider {
  width: 1px;
  height: 16px;
  background: var(--divider-color);
}

.danmaku-toggle,
.quality-filter {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-1) var(--space-2);
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: var(--transition-fast);
  
  .el-icon {
    font-size: 14px;
  }
  
  .toggle-status {
    font-size: var(--font-size-xs);
    padding: 0 4px;
    background: var(--bg-gray-1);
    border-radius: 2px;
  }
  
  &:hover {
    background: var(--bg-hover);
    color: var(--bili-pink);
  }
  
  &.active {
    color: var(--bili-pink);
    
    .toggle-status {
      background: var(--bili-pink-light);
      color: var(--bili-pink);
    }
  }
}

.settings-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: var(--radius-sm);
  color: var(--text-tertiary);
  cursor: pointer;
  transition: var(--transition-fast);
  
  &:hover {
    background: var(--bg-hover);
    color: var(--bili-pink);
  }
}

.toolbar-center {
  flex: 1;
  min-width: 0;
}

.toolbar-right {
  flex-shrink: 0;
  
  .send-tip {
    font-size: var(--font-size-xs);
    color: var(--text-tertiary);
  }
}

/* Danmaku Settings Popover */
.danmaku-settings {
  .setting-item {
    margin-bottom: var(--space-4);
    
    &:last-child {
      margin-bottom: 0;
    }
    
    .setting-label {
      display: block;
      font-size: var(--font-size-sm);
      color: var(--text-secondary);
      margin-bottom: var(--space-2);
    }
  }
}

/* Responsive */
@media (max-width: 768px) {
  .bili-danmaku-toolbar {
    padding: 0 var(--space-3);
    gap: var(--space-2);
  }
  
  .view-count,
  .quality-filter,
  .settings-btn {
    display: none;
  }
  
  .danmaku-toggle span:not(.toggle-status) {
    display: none;
  }
}
</style>
