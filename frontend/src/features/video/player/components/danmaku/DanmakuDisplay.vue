<template>
  <div class="danmaku-layer" :class="{ 'is-hidden': !visible }">
    <div
      v-for="item in items"
      :key="item.key"
      class="danmaku-item"
      :class="{ paused }"
      :style="getItemStyle(item)"
      @animationend="() => emit('finish', item.key)"
    >
      {{ item.text }}
    </div>
  </div>
</template>

<script setup lang="ts">
import type { DanmakuDisplayItem } from "@/shared/types/entity";

const props = defineProps<{
  items: DanmakuDisplayItem[];
  lanes?: number;
  laneHeight?: number;
  duration?: number;
  paused?: boolean;
  visible?: boolean; // 使用 visible 而非 v-if
}>();

const emit = defineEmits<{
  (e: "finish", key: string): void;
}>();

const lanes = props.lanes ?? 10;
const laneHeight = props.laneHeight ?? 32;
const duration = props.duration ?? 10000;

// 计算单个弹幕的样式
const getItemStyle = (item: DanmakuDisplayItem) => {
  const style: Record<string, string> = {
    top: `${(item.lane % lanes) * laneHeight}px`,
    color: item.color,
    animationDuration: `${duration}ms`,
    animationPlayState: props.paused ? "paused" : "running",
  };

  // [Fix]: 关键逻辑
  // 如果有 initialOffset，说明是回退产生的弹幕
  // 设置负的 delay，让动画直接跳到中间位置开始播放
  if (item.initialOffset && item.initialOffset > 0) {
    style.animationDelay = `-${item.initialOffset}ms`;
  }

  return style;
};
</script>

<style scoped lang="scss">
.danmaku-layer {
  position: absolute;
  inset: 0;
  pointer-events: none;
  overflow: hidden;
  z-index: 10;
  // 使用 opacity 切换显隐，保证动画在后台依然计算
  transition: opacity 0.2s ease;
  opacity: 1;

  &.is-hidden {
    opacity: 0;
  }
}

.danmaku-item {
  position: absolute;
  left: 100%;
  white-space: nowrap;
  font-size: 24px; // 调大一点更像 B 站
  font-weight: 600;
  // 强描边，保证在白色背景下也看得清
  text-shadow: 1px 0 1px rgba(0, 0, 0, 0.6), -1px 0 1px rgba(0, 0, 0, 0.6),
    0 1px 1px rgba(0, 0, 0, 0.6), 0 -1px 1px rgba(0, 0, 0, 0.6);
  font-family: SimHei, "Microsoft YaHei", sans-serif;

  animation-name: danmaku-move;
  animation-timing-function: linear;
  animation-fill-mode: forwards;
  will-change: transform;
}

.danmaku-item.paused {
  animation-play-state: paused !important;
}

@keyframes danmaku-move {
  0% {
    transform: translateX(0);
  }
  100% {
    // 确保完全移出屏幕
    transform: translateX(calc(-100% - 100vw));
  }
}
</style>
