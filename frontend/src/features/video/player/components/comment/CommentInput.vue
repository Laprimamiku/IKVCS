<template>
  <div class="comment-input-box" :class="{ 'is-reply': isReply }">
    <div class="avatar-wrap" v-if="!isReply">
      <img
        :src="userAvatar || '/default-avatar.png'"
        alt="avatar"
        class="avatar"
      />
    </div>

    <div class="input-wrap">
      <el-input
        v-model="content"
        type="textarea"
        :rows="isReply ? 2 : 3"
        :placeholder="placeholder"
        resize="none"
        maxlength="1000"
        show-word-limit
        class="custom-textarea"
        :disabled="loading"
      />
      <div class="action-bar">
        <div class="left"></div>
        <div class="right">
          <el-button
            type="primary"
            :loading="loading"
            :disabled="!content.trim()"
            @click="handleSubmit"
            :size="isReply ? 'small' : 'default'"
          >
            {{ isReply ? "回复" : "发表评论" }}
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { useUserStore } from "@/shared/stores/user";
import { storeToRefs } from "pinia";

const props = defineProps<{
  isReply?: boolean;
  placeholder?: string;
  loading?: boolean;
}>();

const emit = defineEmits<{
  (e: "submit", content: string): void;
}>();

const userStore = useUserStore();
const { userInfo } = storeToRefs(userStore);
const userAvatar = userInfo.value?.avatar;

const content = ref("");

const handleSubmit = () => {
  if (!content.value.trim()) return;
  emit("submit", content.value);
  content.value = ""; // 发送后清空
};
</script>

<style scoped lang="scss">
.comment-input-box {
  display: flex;
  gap: 16px;
  margin-bottom: 24px;

  .avatar {
    width: 48px;
    height: 48px;
    border-radius: 50%;
    object-fit: cover;
  }

  .input-wrap {
    flex: 1;

    .action-bar {
      margin-top: 8px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
  }

  // 回复模式样式微调
  &.is-reply {
    margin-bottom: 12px;
    margin-top: 12px;

    .input-wrap {
      margin-left: 0;
    }
  }
}
</style>
