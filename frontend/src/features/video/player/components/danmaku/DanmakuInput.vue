<template>
  <div class="bili-danmaku-input" :class="{ focused: isFocused, disabled: disabled }">
    <!-- Color Picker -->
    <el-popover placement="top" :width="220" trigger="click" :disabled="disabled">
      <template #reference>
        <div class="color-picker-btn" :class="{ disabled }">
          <span class="color-dot" :style="{ background: color }"></span>
          <el-icon class="arrow"><ArrowDown /></el-icon>
        </div>
      </template>
      <div class="color-picker-panel">
        <div class="panel-title">选择弹幕颜色</div>
        <div class="color-grid">
          <div
            v-for="c in presetColors"
            :key="c"
            class="color-item"
            :class="{ active: color === c }"
            :style="{ background: c }"
            @click="color = c"
          >
            <el-icon v-if="color === c" class="check-icon"><Check /></el-icon>
          </div>
        </div>
      </div>
    </el-popover>

    <!-- Input Field -->
    <div class="input-wrapper">
      <input
        v-model="content"
        type="text"
        class="danmaku-text-input"
        :placeholder="disabled ? '登录后发弹幕' : '发个弹幕见证当下'"
        :disabled="disabled"
        @focus="isFocused = true"
        @blur="isFocused = false"
        @keyup.enter="handleSend"
      />
    </div>

    <!-- Send Button -->
    <button 
      class="send-btn" 
      :class="{ disabled: disabled || !content.trim() }"
      :disabled="disabled || sending"
      @click="handleSend"
    >
      <span v-if="!sending">发送</span>
      <el-icon v-else class="loading"><Loading /></el-icon>
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { ElMessage } from "element-plus";
import { ArrowDown, Check, Loading } from "@element-plus/icons-vue";

const props = defineProps<{
  presetColors: string[];
  disabled?: boolean;
  onSend: (content: string, color: string) => Promise<boolean>;
}>();

const content = ref("");
const color = ref(props.presetColors?.[0] || "#ffffff");
const sending = ref(false);
const isFocused = ref(false);

const handleSend = async () => {
  if (props.disabled) {
    ElMessage.warning("请先登录");
    return;
  }
  
  if (!content.value.trim()) {
    ElMessage.warning("请输入弹幕内容");
    return;
  }

  sending.value = true;
  try {
    const ok = await props.onSend(content.value.trim(), color.value);
    if (ok) {
      content.value = "";
      ElMessage.success("弹幕发送成功");
    }
  } catch (error) {
    ElMessage.error("发送失败，请重试");
  } finally {
    sending.value = false;
  }
};
</script>

<style scoped lang="scss">
.bili-danmaku-input {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  height: 36px;
  padding: 0 var(--space-2);
  background: var(--bg-input);
  border: 1px solid transparent;
  border-radius: var(--radius-round);
  transition: var(--transition-base);

  &:hover:not(.disabled) {
    background: var(--bg-white);
    border-color: var(--border-color);
  }

  &.focused {
    background: var(--bg-white);
    border-color: var(--bili-blue);
    box-shadow: 0 0 0 2px var(--bili-blue-light);
  }

  &.disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
}

/* Color Picker Button */
.color-picker-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: var(--space-1);
  cursor: pointer;
  border-radius: var(--radius-sm);
  transition: var(--transition-fast);

  &:hover:not(.disabled) {
    background: var(--bg-hover);
  }

  &.disabled {
    cursor: not-allowed;
  }

  .color-dot {
    width: 18px;
    height: 18px;
    border-radius: var(--radius-circle);
    border: 2px solid var(--bg-white);
    box-shadow: 0 0 0 1px var(--border-color);
  }

  .arrow {
    font-size: 12px;
    color: var(--text-tertiary);
  }
}

/* Color Picker Panel */
.color-picker-panel {
  .panel-title {
    font-size: var(--font-size-sm);
    color: var(--text-secondary);
    margin-bottom: var(--space-3);
  }

  .color-grid {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: var(--space-2);
  }

  .color-item {
    position: relative;
    width: 32px;
    height: 32px;
    border-radius: var(--radius-sm);
    cursor: pointer;
    border: 2px solid transparent;
    transition: var(--transition-fast);

    &:hover {
      transform: scale(1.1);
    }

    &.active {
      border-color: var(--text-primary);
    }

    .check-icon {
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      color: var(--text-white);
      font-size: 16px;
      text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
    }
  }
}

/* Input Wrapper */
.input-wrapper {
  flex: 1;
  min-width: 0;
}

.danmaku-text-input {
  width: 100%;
  height: 100%;
  border: none;
  background: transparent;
  font-size: var(--font-size-sm);
  color: var(--text-primary);
  outline: none;

  &::placeholder {
    color: var(--text-tertiary);
  }

  &:disabled {
    cursor: not-allowed;
  }
}

/* Send Button */
.send-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 52px;
  height: 28px;
  padding: 0 var(--space-3);
  background: var(--bili-blue);
  border: none;
  border-radius: var(--radius-md);
  color: var(--text-white);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  cursor: pointer;
  transition: var(--transition-fast);

  &:hover:not(.disabled) {
    background: var(--bili-blue-hover);
  }

  &.disabled {
    background: var(--bg-gray-2);
    color: var(--text-tertiary);
    cursor: not-allowed;
  }

  .loading {
    animation: spin 1s linear infinite;
  }
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Responsive */
@media (max-width: 768px) {
  .bili-danmaku-input {
    height: 32px;
  }

  .send-btn {
    min-width: 44px;
    height: 24px;
    font-size: var(--font-size-xs);
  }
}
</style>
