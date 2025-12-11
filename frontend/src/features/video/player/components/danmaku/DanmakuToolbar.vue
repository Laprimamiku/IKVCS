<template>
  <div class="danmaku-toolbar">
    <div class="left-controls">
      <span class="online-count">
        <el-icon><User /></el-icon>
        {{ formatNumber(viewCount) }} 人正在看
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
import { User } from "@element-plus/icons-vue";
import DanmakuInput from "./DanmakuInput.vue";
import { formatNumber } from "@/features/video/player/utils/videoFormatters";

const props = defineProps<{
  showDanmaku: boolean;
  viewCount?: number;
  presetColors: string[];
  disabled: boolean;
  onSend: (content: string, color: string) => Promise<boolean>;
}>();

const emit = defineEmits<{
  "update:showDanmaku": [value: boolean];
}>();

// 添加类型安全的处理函数
const handleToggle = (value: boolean | string | number) => {
  // 确保传递的是 boolean 类型
  emit("update:showDanmaku", Boolean(value));
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
    gap: 20px;
    min-width: 140px;

    .online-count {
      font-size: 13px;
      color: #9499a0;
      display: flex;
      align-items: center;
      gap: 4px;
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
