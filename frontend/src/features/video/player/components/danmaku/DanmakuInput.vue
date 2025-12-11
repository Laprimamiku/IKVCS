<template>
  <div class="danmaku-input-container">
    <div class="input-wrapper">
      <el-input
        v-model="content"
        class="no-border-input"
        placeholder="发个弹幕见证当下"
        @keyup.enter="handleSend"
      />
    </div>

    <div class="right-actions">
      <el-popover placement="top" :width="200" trigger="click">
        <template #reference>
          <div class="style-btn" :style="{ color: color }">
            <span class="color-indicator" :style="{ background: color }"></span>
          </div>
        </template>
        <div class="color-grid">
          <div
            v-for="c in presetColors"
            :key="c"
            class="color-block"
            :style="{ background: c }"
            @click="color = c"
          ></div>
        </div>
      </el-popover>

      <el-button
        type="primary"
        class="send-btn"
        :loading="sending"
        @click="handleSend"
      >
        发送
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
// (逻辑保持原有代码不变，主要是 Template 和 Style 变了)
import { ref } from "vue";
import { ElMessage } from "element-plus";

const props = defineProps<{
  presetColors: string[];
  disabled?: boolean;
  onSend: (content: string, color: string) => Promise<boolean>;
}>();

const content = ref("");
const color = ref(props.presetColors?.[0] || "#ffffff");
const sending = ref(false);

const handleSend = async () => {
  if (props.disabled) return ElMessage.warning("请先登录");
  if (!content.value.trim()) return ElMessage.warning("请输入内容");

  sending.value = true;
  try {
    const ok = await props.onSend(content.value.trim(), color.value);
    if (ok) content.value = "";
  } finally {
    sending.value = false;
  }
};
</script>

<style scoped lang="scss">
.danmaku-input-container {
  display: flex;
  align-items: center;
  background: #f1f2f3; // B站输入框背景色
  border-radius: 8px;
  padding: 4px;
  transition: background 0.2s;

  &:focus-within {
    background: #fff;
    border: 1px solid #e3e5e7;
  }
}

.input-wrapper {
  flex: 1;
  :deep(.el-input__wrapper) {
    box-shadow: none !important;
    background: transparent !important;
  }
}

.right-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-right: 4px;
}

.style-btn {
  cursor: pointer;
  padding: 4px;
  display: flex;
  align-items: center;
  .color-indicator {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    border: 2px solid #fff;
    box-shadow: 0 0 2px rgba(0, 0, 0, 0.2);
  }
}

.send-btn {
  border-radius: 6px;
  background: #00aeec;
  border-color: #00aeec;
  min-width: 60px;
  &:hover {
    background: #00b5f5;
    border-color: #00b5f5;
  }
}

.color-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 8px;
  .color-block {
    width: 24px;
    height: 24px;
    border-radius: 4px;
    cursor: pointer;
    border: 1px solid #e3e5e7;
    &:hover {
      transform: scale(1.1);
    }
  }
}
</style>
