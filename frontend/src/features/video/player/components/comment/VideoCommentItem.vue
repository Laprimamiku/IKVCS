<template>
  <div class="comment-item">
    <div class="user-avatar">
      <el-avatar
        :size="40"
        :src="comment.user.avatar || '/default-avatar.png'"
      />
    </div>

    <div class="content-container">
      <div class="user-info">
        <span class="nickname" :class="{ 'is-uploader': isUploader }">{{
          comment.user.nickname
        }}</span>

        <div class="ai-tags" v-if="comment.ai_score">
          <el-tag
            v-if="comment.ai_score >= 85"
            size="small"
            effect="dark"
            color="#FFD700"
            class="ai-tag high-quality"
          >
            <span class="tag-icon">🔥</span> 优质
          </el-tag>

          <el-tag
            v-else-if="comment.ai_label && comment.ai_label !== '普通'"
            size="small"
            effect="plain"
            type="info"
            class="ai-tag"
          >
            {{ comment.ai_label }}
          </el-tag>
        </div>
      </div>

      <p class="text-content">
        {{ comment.content }}
      </p>

      <div class="action-footer">
        <span class="time">{{ formatDate(comment.created_at) }}</span>

        <span class="action-btn like-btn">
          <el-icon><Pointer /></el-icon>
          {{ comment.like_count || "点赞" }}
        </span>

        <span class="action-btn reply-btn" @click="toggleReplyBox"> 回复 </span>
      </div>

      <div v-if="showReplyBox">
        <CommentInput
          :is-reply="true"
          :loading="submitting"
          :placeholder="`回复 @${comment.user.nickname}:`"
          @submit="handleReplySubmit"
        />
      </div>

      <div
        class="sub-comments"
        v-if="comment.replies && comment.replies.length > 0"
      >
        <div
          v-for="reply in comment.replies"
          :key="reply.id"
          class="sub-comment-item"
        >
          <div class="sub-user-info">
            <span class="sub-nickname">{{ reply.user.nickname }}</span>
            <span
              v-if="reply.ai_label && reply.ai_label !== '普通'"
              class="mini-ai-tag"
            >
              {{ reply.ai_label }}
            </span>
            :
            <span class="sub-content">{{ reply.content }}</span>
          </div>
          <div class="sub-footer">
            <span class="time">{{ formatDate(reply.created_at) }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from "vue";
import { Pointer } from "@element-plus/icons-vue";
import type { Comment } from "@/shared/types/entity";
import { formatTimeAgo } from "@/shared/utils/formatters"; // 假设你有这个工具，或者用 dayjs
import CommentInput from "./CommentInput.vue";

const props = defineProps<{
  comment: Comment;
  uploaderId?: number;
}>();

const emit = defineEmits<{
  (e: "reply", content: string, parentId: number): Promise<void>;
}>();

const showReplyBox = ref(false);
const submitting = ref(false);

const isUploader = computed(() => props.comment.user_id === props.uploaderId);

const formatDate = (dateStr: string) => {
  // 简单格式化，建议使用 dayjs 或 date-fns
  return new Date(dateStr).toLocaleDateString();
};

const toggleReplyBox = () => {
  showReplyBox.value = !showReplyBox.value;
};

const handleReplySubmit = async (content: string) => {
  submitting.value = true;
  try {
    await emit("reply", content, props.comment.id);
    showReplyBox.value = false;
  } finally {
    submitting.value = false;
  }
};
</script>

<style scoped lang="scss">
.comment-item {
  display: flex;
  gap: 16px;
  padding: 16px 0;
  border-bottom: 1px solid #f1f2f3;

  .content-container {
    flex: 1;

    .user-info {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 6px;

      .nickname {
        font-size: 13px;
        color: #61666d;
        font-weight: 500;
        cursor: pointer;

        &.is-uploader {
          color: #ff6699;
        }
      }

      .ai-tags {
        display: flex;
        gap: 6px;

        .ai-tag {
          border: none;

          &.high-quality {
            color: #5a3a00; // 金色背景下的深色文字
            font-weight: bold;
          }
        }
      }
    }

    .text-content {
      font-size: 15px;
      color: #18191c;
      line-height: 24px;
      margin: 0 0 8px;
      white-space: pre-wrap;
    }

    .action-footer {
      display: flex;
      align-items: center;
      gap: 20px;
      font-size: 13px;
      color: #9499a0;

      .action-btn {
        cursor: pointer;
        display: flex;
        align-items: center;
        gap: 4px;
        &:hover {
          color: #00aeec;
        }
      }
    }

    .sub-comments {
      margin-top: 12px;
      background: #f9f9f9;
      padding: 12px;
      border-radius: 4px;

      .sub-comment-item {
        margin-bottom: 8px;
        font-size: 13px;
        line-height: 20px;

        .sub-nickname {
          color: #61666d;
          font-weight: 500;
          cursor: pointer;
        }

        .mini-ai-tag {
          font-size: 10px;
          background: #e3e5e7;
          color: #9499a0;
          padding: 0 2px;
          border-radius: 2px;
          margin: 0 2px;
        }

        .sub-footer {
          margin-top: 2px;
          font-size: 12px;
          color: #9499a0;
        }
      }
    }
  }
}
</style>
