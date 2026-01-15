<template>
  <div class="bili-comment-input" :class="{ 'is-reply': isReply, 'is-focused': isFocused }">
    <!-- Avatar (only for root comments) -->
    <div class="avatar-wrap" v-if="!isReply">
      <el-avatar :src="userStore.avatar" :size="48" class="user-avatar">
        {{ userStore.userInfo?.nickname?.charAt(0).toUpperCase() || 'U' }}
      </el-avatar>
    </div>

    <!-- Input Area -->
    <div class="input-container">
      <div class="input-wrapper" :class="{ focused: isFocused }">
        <textarea
          ref="textareaRef"
          v-model="content"
          :rows="isFocused || isReply ? 3 : 1"
          :placeholder="placeholder"
          maxlength="1000"
          :disabled="loading"
          class="comment-textarea"
          @focus="handleFocus"
          @blur="handleBlur"
          @input="autoResize"
        />
        
        <!-- Character Count -->
        <span v-if="isFocused && content.length > 0" class="char-count">
          {{ content.length }}/1000
        </span>
      </div>

      <!-- Action Bar (visible when focused or has content) -->
      <transition name="slide-fade">
        <div v-if="isFocused || content.trim()" class="action-bar">
          <div class="action-left">
            <!-- Emoji Button (placeholder) -->
            <button class="action-btn emoji-btn" title="表情">
              <el-icon class="btn-icon"><Sunny /></el-icon>
            </button>
            <!-- Image Button (placeholder) -->
            <button class="action-btn image-btn" title="图片">
              <el-icon class="btn-icon"><Picture /></el-icon>
            </button>
          </div>

          <div class="action-right">
            <button
              class="submit-btn"
              :class="{ 
                'is-active': content.trim(),
                'is-loading': loading 
              }"
              :disabled="!content.trim() || loading"
              @click="handleSubmit"
            >
              <span v-if="loading" class="loading-spinner"></span>
              <span v-else>{{ isReply ? '回复' : '发布' }}</span>
            </button>
          </div>
        </div>
      </transition>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick } from "vue";
import { Sunny, Picture } from "@element-plus/icons-vue";
import { useUserStore } from "@/shared/stores/user";

const userStore = useUserStore();

const props = withDefaults(defineProps<{
  isReply?: boolean;
  placeholder?: string;
  loading?: boolean;
}>(), {
  placeholder: '发一条友善的评论吧~',
});

const emit = defineEmits<{
  (e: "submit", content: string): void;
}>();

const content = ref("");
const isFocused = ref(false);
const textareaRef = ref<HTMLTextAreaElement | null>(null);

const handleFocus = () => {
  isFocused.value = true;
};

const handleBlur = () => {
  // Delay blur to allow button click
  setTimeout(() => {
    if (!content.value.trim()) {
      isFocused.value = false;
    }
  }, 150);
};

const autoResize = () => {
  nextTick(() => {
    if (textareaRef.value) {
      textareaRef.value.style.height = 'auto';
      textareaRef.value.style.height = Math.min(textareaRef.value.scrollHeight, 150) + 'px';
    }
  });
};

const handleSubmit = () => {
  if (!content.value.trim()) return;
  emit("submit", content.value);
  content.value = "";
  isFocused.value = false;
  
  // Reset textarea height
  if (textareaRef.value) {
    textareaRef.value.style.height = 'auto';
  }
};
</script>

<style scoped lang="scss">
.bili-comment-input {
  display: flex;
  gap: var(--space-3);
  margin-bottom: var(--space-6);

  /* Avatar */
  .avatar-wrap {
    flex-shrink: 0;
  }

  .user-avatar {
    width: 48px;
    height: 48px;
    border-radius: var(--radius-circle);
    object-fit: cover;
    border: 2px solid var(--bg-gray-1);
    transition: border-color var(--transition-base);
  }

  &.is-focused .user-avatar {
    border-color: var(--primary-color);
  }

  /* Input Container */
  .input-container {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
  }

  /* Input Wrapper */
  .input-wrapper {
    position: relative;
    background: var(--bg-gray-1);
    border-radius: var(--radius-lg);
    border: 1px solid transparent;
    transition: all var(--transition-base);

    &:hover {
      background: var(--bg-hover);
    }

    &.focused {
      background: var(--bg-white);
      border-color: var(--primary-color);
      box-shadow: 0 0 0 2px var(--primary-light);
    }
  }

  /* Textarea */
  .comment-textarea {
    width: 100%;
    padding: var(--space-3) var(--space-4);
    font-size: var(--font-size-base);
    font-family: inherit;
    color: var(--text-primary);
    background: transparent;
    border: none;
    outline: none;
    resize: none;
    line-height: var(--line-height-normal);
    min-height: 40px;
    max-height: 150px;
    transition: min-height var(--transition-base);

    &::placeholder {
      color: var(--text-tertiary);
    }

    &:disabled {
      cursor: not-allowed;
      opacity: 0.6;
    }
  }

  /* Character Count */
  .char-count {
    position: absolute;
    right: var(--space-3);
    bottom: var(--space-2);
    font-size: var(--font-size-xs);
    color: var(--text-quaternary);
  }

  /* Action Bar */
  .action-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 var(--space-1);
  }

  .action-left {
    display: flex;
    gap: var(--space-1);
  }

  .action-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    background: transparent;
    border: none;
    border-radius: var(--radius-md);
    cursor: pointer;
    transition: all var(--transition-base);

    .btn-icon {
      font-size: var(--font-size-lg);
      opacity: 0.6;
      transition: opacity var(--transition-base);
    }

    &:hover {
      background: var(--bg-gray-1);

      .btn-icon {
        opacity: 1;
      }
    }
  }

  /* Submit Button */
  .submit-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    min-width: 70px;
    height: 32px;
    padding: 0 var(--space-4);
    font-size: var(--font-size-sm);
    font-weight: var(--font-weight-medium);
    color: var(--text-quaternary);
    background: var(--bg-gray-2);
    border: none;
    border-radius: var(--radius-round);
    cursor: not-allowed;
    transition: all var(--transition-base);

    &.is-active {
      color: var(--text-white);
      background: var(--primary-gradient);
      cursor: pointer;

      &:hover {
        opacity: 0.9;
        transform: translateY(-1px);
      }

      &:active {
        transform: translateY(0);
      }
    }

    &.is-loading {
      cursor: wait;
    }

    .loading-spinner {
      width: 14px;
      height: 14px;
      border: 2px solid rgba(255, 255, 255, 0.3);
      border-top-color: white;
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }
  }

  /* Reply Mode */
  &.is-reply {
    margin-bottom: var(--space-3);
    margin-top: var(--space-3);

    .input-wrapper {
      background: var(--bg-white);
      border: 1px solid var(--border-color);

      &.focused {
        border-color: var(--primary-color);
      }
    }

    .comment-textarea {
      padding: var(--space-2) var(--space-3);
      font-size: var(--font-size-sm);
      min-height: 32px;
    }

    .submit-btn {
      height: 28px;
      min-width: 60px;
      font-size: var(--font-size-xs);
    }
  }
}

/* Transitions */
.slide-fade-enter-active,
.slide-fade-leave-active {
  transition: all var(--transition-base);
}

.slide-fade-enter-from,
.slide-fade-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
