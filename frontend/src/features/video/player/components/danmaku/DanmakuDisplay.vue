<template>
  <div class="danmaku-layer" :class="{ 'is-hidden': !visible }">
    <template v-for="item in items" :key="item.key">
      <div
        class="danmaku-item"
        :class="{
          paused,
          'is-highlight': isHighlight(item),
          'is-top': item.type === 'top',
          'is-bottom': item.type === 'bottom',
          'is-filtered': shouldFilter(item), // 使用 CSS class 控制显示/隐藏，不重置动画
        }"
        :style="getItemStyle(item)"
        @animationend="() => emit('finish', item.key)"
        @mousedown.stop
        @click.stop="handleDanmakuClick(item)"
      >
        <el-icon v-if="isHighlight(item)" class="hq-icon" :size="14">
          <Star />
        </el-icon>
        {{ item.text }}
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ElMessage, ElMessageBox } from "element-plus";
import { Star } from "@element-plus/icons-vue";
import type { DanmakuDisplayItem } from "@/shared/types/entity";
import { createReport } from "@/features/video/player/api/report.api";
import { useUserStore } from "@/shared/stores/user";

const props = defineProps<{
  items: DanmakuDisplayItem[];
  lanes?: number;
  laneHeight?: number;
  duration?: number;
  paused?: boolean;
  visible?: boolean; // 使用 visible 而非 v-if
  filterLowScore?: boolean; // [New] 新增过滤属性
}>();

const emit = defineEmits<{
  (e: "finish", key: string): void;
}>();

const userStore = useUserStore();

// 处理弹幕点击举报
const handleDanmakuClick = async (item: DanmakuDisplayItem) => {
  if (!userStore.isLoggedIn) {
    ElMessage.warning("请先登录");
    return;
  }

  // 如果没有id（可能是实时弹幕还未保存），提示用户
  if (!item.id) {
    ElMessage.warning("该弹幕暂时无法举报，请稍后再试");
    return;
  }

  try {
    const { value: reason } = await ElMessageBox.prompt(
      `举报弹幕："${item.text}"`,
      "举报弹幕",
      {
        confirmButtonText: "提交",
        cancelButtonText: "取消",
        inputPlaceholder: "请简要说明举报原因",
        inputValidator: (value) => {
          if (!value || value.trim().length === 0) {
            return "请输入举报原因";
          }
          if (value.length > 100) {
            return "举报原因不能超过100个字符";
          }
          return true;
        },
      }
    );

    const res = await createReport({
      target_type: "DANMAKU",
      target_id: item.id,
      reason: reason.trim(),
    });

    if (res.success) {
      ElMessage.success(res.data?.message || "举报提交成功，我们会尽快处理");
    } else {
      ElMessage.error("举报提交失败，请稍后重试");
    }
  } catch (error: unknown) {
    if (error !== "cancel") {
      console.error("举报失败:", error);
      const errorMsg =
        error?.response?.data?.detail ||
        error?.message ||
        "举报提交失败，请稍后重试";
      ElMessage.error(errorMsg);
    }
  }
};

const lanes = props.lanes ?? 10;
const laneHeight = props.laneHeight ?? 32;
const duration = props.duration ?? 10000;

// [New] 判断是否为优质弹幕
// 分数 >= 85 或后端标记为 highlight
const isHighlight = (item: DanmakuDisplayItem) => {
  return (item.ai_score && item.ai_score >= 85) || item.is_highlight;
};

// [New] 过滤逻辑
// 注意：这里返回 true 表示应该隐藏，false 表示应该显示
// 与弹幕显示开关的逻辑一致：使用 CSS 控制显示/隐藏，不删除 DOM 元素
const shouldFilter = (item: DanmakuDisplayItem) => {
  if (!props.filterLowScore) return false;
  // 如果开启过滤，且分数存在且 < 70，则隐藏
  // 新发弹幕无分数(undefined)不应被过滤
  return item.ai_score !== undefined && item.ai_score < 70;
};

// 计算单个弹幕样式
const getItemStyle = (item: DanmakuDisplayItem) => {
  const style: Record<string, string> = {
    top: `${(item.lane % lanes) * laneHeight}px`,
    color: item.color,
    animationDuration: `${duration}ms`,
    animationPlayState: props.paused ? "paused" : "running",
  };

  // [Fix] 回退弹幕：负 delay 直接跳到中间进度
  if (item.initialOffset && item.initialOffset > 0) {
    style.animationDelay = `-${item.initialOffset}ms`;
  }

  // [New] 优质弹幕额外样式
  if (isHighlight(item)) {
    style.zIndex = "100";
    style.fontWeight = "800";
    // 白色弹幕强制转为金色
    if (item.color.toLowerCase() === "#ffffff") {
      style.color = "#ffd700";
    }
  }

  return style;
};
</script>

<style scoped lang="scss">
/* ===============================
   Bilibili-Style Danmaku Display
   =============================== */
.danmaku-layer {
  position: absolute;
  inset: 0;
  pointer-events: none;
  overflow: hidden;
  z-index: 10;
  transition: opacity var(--transition-base);
  opacity: 1;

  &.is-hidden {
    opacity: 0;
    pointer-events: none;
  }
}

.danmaku-item {
  position: absolute;
  left: 100%;
  white-space: nowrap;
  font-size: var(--danmaku-font-size, 25px);
  font-weight: 600;
  font-family: 'SimHei', 'Microsoft YaHei', 'PingFang SC', sans-serif;
  letter-spacing: 0.5px;
  line-height: 1.3;

  // Bilibili-style text stroke for readability
  text-shadow: 
    1px 0 1px rgba(0, 0, 0, 0.7),
    -1px 0 1px rgba(0, 0, 0, 0.7),
    0 1px 1px rgba(0, 0, 0, 0.7),
    0 -1px 1px rgba(0, 0, 0, 0.7),
    1px 1px 1px rgba(0, 0, 0, 0.5),
    -1px -1px 1px rgba(0, 0, 0, 0.5);

  animation-name: danmaku-scroll;
  animation-timing-function: linear;
  animation-fill-mode: forwards;
  will-change: transform;
  backface-visibility: hidden;
  transform: translateZ(0);

  display: flex;
  align-items: center;
  gap: var(--space-1);

  // Enable click for reporting
  pointer-events: auto;
  cursor: pointer;
  transition: 
    opacity var(--transition-fast),
    transform var(--transition-fast);
  border-radius: var(--radius-xs);
  padding: var(--space-0-5) var(--space-1);

  &:hover {
    opacity: 0.85;
    z-index: 999;
    background: rgba(0, 0, 0, 0.4);
    transform: scale(1.02);
  }

  // Paused state
  &.paused {
    animation-play-state: paused !important;
  }

  // Top fixed danmaku (centered)
  &.is-top {
    left: 50%;
    transform: translateX(-50%);
    animation: none;
    text-align: center;
  }

  // Bottom fixed danmaku (centered)
  &.is-bottom {
    left: 50%;
    bottom: 60px;
    top: auto;
    transform: translateX(-50%);
    animation: none;
    text-align: center;
  }

  // Filtered danmaku (hidden but animation continues)
  // 使用 opacity 和 pointer-events 控制显示，不改变 display，避免重置动画
  &.is-filtered {
    opacity: 0;
    pointer-events: none;
  }

  /* ===============================
     Premium/Highlight Danmaku Style
     =============================== */
  &.is-highlight {
    font-size: calc(var(--danmaku-font-size, 25px) + 3px);
    font-weight: 700;
    
    // Golden glow effect
    text-shadow: 
      0 0 8px rgba(255, 215, 0, 0.8),
      0 0 16px rgba(255, 215, 0, 0.4),
      1px 1px 2px rgba(0, 0, 0, 0.9),
      -1px -1px 2px rgba(0, 0, 0, 0.9);
    
    // Premium background
    background: linear-gradient(
      135deg,
      rgba(255, 215, 0, 0.15) 0%,
      rgba(255, 165, 0, 0.1) 100%
    );
    padding: 4px 10px;
    border-radius: var(--radius-sm);
    border: 1px solid rgba(255, 215, 0, 0.5);
    box-shadow: 
      0 0 12px rgba(255, 215, 0, 0.3),
      inset 0 0 8px rgba(255, 215, 0, 0.1);
    
    z-index: 100;

    &:hover {
      background: linear-gradient(
        135deg,
        rgba(255, 215, 0, 0.25) 0%,
        rgba(255, 165, 0, 0.2) 100%
      );
      box-shadow: 
        0 0 20px rgba(255, 215, 0, 0.5),
        inset 0 0 12px rgba(255, 215, 0, 0.15);
    }
  }

  // Premium icon
  .hq-icon {
    font-size: 0.85em;
    filter: drop-shadow(0 0 4px rgba(255, 215, 0, 0.8));
    animation: sparkle 1.5s ease-in-out infinite;
  }
}

// Scroll animation
@keyframes danmaku-scroll {
  0% {
    transform: translateX(0);
  }
  100% {
    transform: translateX(calc(-100% - 100vw));
  }
}

// Sparkle animation for premium icon
@keyframes sparkle {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.7;
    transform: scale(1.1);
  }
}
</style>
