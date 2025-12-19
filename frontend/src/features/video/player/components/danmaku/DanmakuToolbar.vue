<template>
  <div class="danmaku-toolbar">
    <div class="left-controls">
      <span class="online-count" v-if="viewCount !== undefined && viewCount !== null">
        <el-icon><User /></el-icon>
        {{ formatNumber(viewCount) }} 播放
      </span>

      <div class="switch-wrapper">
        <el-switch
          :model-value="showDanmaku"
          @update:model-value="handleToggle"
          inline-prompt
          active-text="弹"
          inactive-text="关"
          style="--el-switch-on-color: #fb7299"
        />
      </div>

      <div class="filter-wrapper" title="开启后将隐藏AI评分低于60的弹幕">
        <el-switch
          v-model="internalFilterState"
          inline-prompt
          active-text="精"
          inactive-text="全"
          style="--el-switch-on-color: #e6a23c"
          @change="handleFilterChange"
        />
      </div>
    </div>

    <div class="input-area">
      <DanmakuInput
        class="custom-danmaku-input"
        :preset-colors="presetColors"
        :disabled="disabled"
        :on-send="onSend"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from "vue";
import { User } from "@element-plus/icons-vue";
import DanmakuInput from "./DanmakuInput.vue";
import { formatNumber } from "@/features/video/player/utils/videoFormatters";

const props = defineProps<{
  showDanmaku: boolean;
  filterLowScore?: boolean; // 接收外部传入的过滤状态
  viewCount?: number;
  presetColors: string[];
  disabled: boolean;
  onSend: (content: string, color: string) => Promise<boolean>;
}>();

const emit = defineEmits<{
  "update:showDanmaku": [value: boolean];
  "update:filterLowScore": [value: boolean]; // 发出过滤状态变更事件
}>();

// 本地状态同步 (以便 v-model 正常工作)
const internalFilterState = ref(props.filterLowScore || false);
watch(
  () => props.filterLowScore,
  (val) => {
    if (val !== undefined) internalFilterState.value = val;
  }
);

// 处理弹幕显示开关
const handleToggle = (value: boolean | string | number) => {
  emit("update:showDanmaku", Boolean(value));
};

// [修复] 处理低分过滤开关：显式转换类型以解决 TS 报错
const handleFilterChange = (value: boolean | string | number) => {
  // Element Plus 的 switch change 事件类型宽泛，这里强制转为 boolean
  emit("update:filterLowScore", Boolean(value));
};
</script>

<style lang="scss" scoped>
.danmaku-toolbar {
  height: 46px;
  margin-top: 10px;
  background: #fff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  border-radius: 4px;
  display: flex;
  align-items: center;
  padding: 0 16px;
  gap: 16px;
  border: 1px solid #f1f2f3;

  .left-controls {
    display: flex;
    align-items: center;
    gap: 12px;
    min-width: 140px;

    .online-count {
      font-size: 13px;
      color: #9499a0;
      display: flex;
      align-items: center;
      gap: 4px;
    }

    .switch-wrapper,
    .filter-wrapper {
      display: flex;
      align-items: center;
    }
  }

  .input-area {
    flex: 1;

    :deep(.danmaku-input) {
      background: #f1f2f3;
      border-radius: 6px;
      padding: 4px 10px;
      color: #18191c;
      box-shadow: none;
      border: 1px solid transparent;
      transition: all 0.2s;

      &:focus-within {
        background: #fff;
        border-color: #e3e5e7;
      }

      input {
        color: #18191c;
      }

      .el-input__wrapper {
        background: transparent !important;
        box-shadow: none !important;
      }

      .color-dot {
        box-shadow: 0 0 2px rgba(0, 0, 0, 0.2);
      }
    }
  }
}
</style>
