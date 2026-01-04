<template>
  <div class="bili-comment-item">
    <!-- User Avatar -->
    <div class="avatar-col">
      <img
        :src="comment.user.avatar || '/default-avatar.png'"
        alt="avatar"
        class="user-avatar"
      />
    </div>

    <!-- Content Column -->
    <div class="content-col">
      <!-- User Info Row -->
      <div class="user-row">
        <span class="username" :class="{ 'is-uploader': isUploader }">
          {{ comment.user.nickname }}
        </span>
        
        <!-- UP主标识 -->
        <span v-if="isUploader" class="up-badge">UP主</span>
        
        <!-- AI Quality Tags -->
        <div class="ai-badges" v-if="comment.ai_score">
          <span v-if="comment.ai_score >= 85" class="ai-badge premium">
            <el-icon class="badge-icon" :size="12"><Star /></el-icon>
            优质评论
          </span>
          <span 
            v-else-if="comment.ai_label && comment.ai_label !== '普通'" 
            class="ai-badge normal"
          >
            {{ comment.ai_label }}
          </span>
        </div>
      </div>

      <!-- Comment Content -->
      <p class="comment-text">{{ comment.content }}</p>

      <!-- Action Row -->
      <div class="action-row">
        <span class="publish-time">{{ formatDate(comment.created_at) }}</span>

        <!-- Like Button -->
        <button 
          class="action-btn like-btn"
          :class="{ active: localIsLiked }"
          @click="handleLike"
        >
          <el-icon class="btn-icon like-icon" :class="{ 'is-liked': localIsLiked }"><CircleCheckFilled /></el-icon>
          <span class="btn-text">{{ localLikeCount || '' }}</span>
        </button>

        <!-- Dislike Button (visual only) -->
        <button class="action-btn dislike-btn">
          <el-icon class="btn-icon"><Minus /></el-icon>
        </button>

        <!-- Reply Button -->
        <button class="action-btn reply-btn" @click="toggleReplyBox">
          <el-icon class="btn-icon"><ChatDotRound /></el-icon>
          <span class="btn-text">回复</span>
        </button>

        <!-- More Actions -->
        <button class="action-btn more-btn" @click="handleReport">
          <el-icon class="btn-icon"><Warning /></el-icon>
          <span class="btn-text">举报</span>
        </button>
      </div>

      <!-- Reply Input Box -->
      <transition name="expand">
        <div v-if="showReplyBox" class="reply-input-wrap">
          <CommentInput
            :is-reply="true"
            :loading="submitting"
            :placeholder="replyToUser ? `回复 @${replyToUser.nickname}：` : `回复 @${comment.user.nickname}：`"
            @submit="handleReplySubmit"
          />
        </div>
      </transition>

      <!-- Sub Comments / Replies -->
      <div 
        v-if="comment.replies && comment.replies.length > 0" 
        class="replies-container"
      >
        <div
          v-for="reply in displayedReplies"
          :key="reply.id"
          class="reply-item"
        >
          <img
            :src="reply.user.avatar || '/default-avatar.png'"
            alt="avatar"
            class="reply-avatar"
          />
          <div class="reply-content">
            <div class="reply-header">
              <span class="reply-username">{{ reply.user.nickname }}</span>
              <span v-if="reply.ai_label && reply.ai_label !== '普通'" class="reply-ai-tag">
                {{ reply.ai_label }}
              </span>
            </div>
            <p class="reply-text">
              <span v-if="reply.reply_to_user" class="reply-to-mention">@{{ reply.reply_to_user.nickname }} </span>
              {{ reply.content }}
            </p>
            <div class="reply-footer">
              <span class="reply-time">{{ formatDate(reply.created_at) }}</span>
              <button 
                class="reply-action like-btn"
                :class="{ active: reply.is_liked }"
                @click="handleReplyLike(reply)"
              >
                <el-icon><Like /></el-icon>
                <span>{{ reply.like_count || '' }}</span>
              </button>
              <button 
                class="reply-action" 
                @click="handleReplyToReply(reply)"
              >
                回复
              </button>
            </div>
          </div>
        </div>

        <!-- Show More Replies -->
        <button 
          v-if="comment.replies.length > 3 && !showAllReplies"
          class="show-more-replies"
          @click="showAllReplies = true"
        >
          <span>共 {{ comment.replies.length }} 条回复</span>
          <i class="arrow">▼</i>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Star, CircleCheckFilled, Minus, ChatDotRound, Warning } from "@element-plus/icons-vue";
import type { Comment } from "@/shared/types/entity";
import { toggleCommentLike } from "@/features/video/player/api/comment.api";
import { createReport } from "@/features/video/player/api/report.api";
import { useUserStore } from "@/shared/stores/user";
import CommentInput from "./CommentInput.vue";

const props = defineProps<{
  comment: Comment;
  uploaderId?: number;
}>();

const emit = defineEmits<{
  (e: "reply", content: string, parentId: number, replyToUserId?: number | null): Promise<void>;
}>();

const userStore = useUserStore();

// Reply state
const showReplyBox = ref(false);
const submitting = ref(false);
const showAllReplies = ref(false);
const replyToUser = ref<{ id: number; nickname: string } | null>(null); // 回复目标用户

// Like state (optimistic update)
const localIsLiked = ref(!!props.comment.is_liked);
const localLikeCount = ref(props.comment.like_count || 0);

// Computed
const isUploader = computed(() => props.comment.user_id === props.uploaderId);

const displayedReplies = computed(() => {
  if (!props.comment.replies) return [];
  return showAllReplies.value 
    ? props.comment.replies 
    : props.comment.replies.slice(0, 3);
});

// Format date
const formatDate = (dateStr: string) => {
  const date = new Date(dateStr);
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);
  
  if (minutes < 1) return '刚刚';
  if (minutes < 60) return `${minutes}分钟前`;
  if (hours < 24) return `${hours}小时前`;
  if (days < 7) return `${days}天前`;
  
  return date.toLocaleDateString('zh-CN', {
    month: 'numeric',
    day: 'numeric',
  });
};

// Toggle reply box
const toggleReplyBox = () => {
  showReplyBox.value = !showReplyBox.value;
  if (showReplyBox.value) {
    // 回复根评论时，@ 评论作者
    replyToUser.value = props.comment.user;
  } else {
    replyToUser.value = null;
  }
};

// Handle reply to reply (二级评论的回复)
const handleReplyToReply = (reply: Comment) => {
  showReplyBox.value = true;
  // 回复二级评论时，@ 被回复的用户
  replyToUser.value = reply.user;
};

// Submit reply
const handleReplySubmit = async (content: string) => {
  submitting.value = true;
  try {
    await emit("reply", content, props.comment.id, replyToUser.value?.id || null);
    showReplyBox.value = false;
    replyToUser.value = null;
  } finally {
    submitting.value = false;
  }
};

// Handle reply like
const handleReplyLike = async (reply: Comment) => {
  if (!userStore.isLoggedIn) {
    ElMessage.warning("请先登录");
    return;
  }

  const prevState = reply.is_liked;
  const prevCount = reply.like_count || 0;

  // Optimistic update
  reply.is_liked = !reply.is_liked;
  reply.like_count = (reply.like_count || 0) + (reply.is_liked ? 1 : -1);

  try {
    const response = await toggleCommentLike(reply.id);
    if (response.success && response.data) {
      reply.is_liked = response.data.is_liked;
      reply.like_count = response.data.like_count;
    }
  } catch (e) {
    // Rollback
    reply.is_liked = prevState;
    reply.like_count = prevCount;
    ElMessage.error("点赞失败，请重试");
  }
};

// Like handler (optimistic update)
const handleLike = async () => {
  if (!userStore.isLoggedIn) {
    ElMessage.warning("请先登录");
    return;
  }

  const prevState = localIsLiked.value;
  const prevCount = localLikeCount.value;

  // Optimistic update
  localIsLiked.value = !localIsLiked.value;
  localLikeCount.value += localIsLiked.value ? 1 : -1;

  try {
    const response = await toggleCommentLike(props.comment.id);
    if (response.success && response.data) {
      localIsLiked.value = response.data.is_liked;
      localLikeCount.value = response.data.like_count;
      props.comment.is_liked = response.data.is_liked;
      props.comment.like_count = response.data.like_count;
    }
  } catch (e) {
    // Rollback
    localIsLiked.value = prevState;
    localLikeCount.value = prevCount;
    ElMessage.error("点赞失败，请重试");
  }
};

// Report handler
const handleReport = async () => {
  if (!userStore.isLoggedIn) {
    ElMessage.warning("请先登录");
    return;
  }
  
  try {
    const { value: reason } = await ElMessageBox.prompt(
      '请输入举报原因',
      '举报评论',
      {
        confirmButtonText: '提交',
        cancelButtonText: '取消',
        inputPlaceholder: '请简要说明举报原因',
        inputValidator: (value) => {
          if (!value || value.trim().length === 0) return '请输入举报原因';
          if (value.length > 100) return '举报原因不能超过100个字符';
          return true;
        }
      }
    );
    
    const res = await createReport({
      target_type: 'COMMENT',
      target_id: props.comment.id,
      reason: reason.trim(),
    });
    
    if (res.success) {
      ElMessage.success(res.data?.message || '举报提交成功');
    } else {
      ElMessage.error('举报提交失败');
    }
  } catch (error: unknown) {
    if (error !== 'cancel') {
      console.error('举报失败:', error);
      ElMessage.error(error?.response?.data?.detail || '举报提交失败');
    }
  }
};
</script>

<style scoped lang="scss">
.bili-comment-item {
  display: flex;
  gap: var(--space-3);
  padding: var(--space-4) 0;
  border-bottom: 1px solid var(--border-light);
  transition: background var(--transition-base);

  &:hover {
    background: var(--bg-hover);
    margin: 0 calc(var(--space-3) * -1);
    padding-left: var(--space-3);
    padding-right: var(--space-3);
    border-radius: var(--radius-md);
  }

  &:last-child {
    border-bottom: none;
  }
}

/* Avatar */
.avatar-col {
  flex-shrink: 0;
}

.user-avatar {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-circle);
  object-fit: cover;
  cursor: pointer;
  transition: transform var(--transition-base);

  &:hover {
    transform: scale(1.05);
  }
}

/* Content */
.content-col {
  flex: 1;
  min-width: 0;
}

/* User Row */
.user-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-bottom: var(--space-2);
}

.username {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--text-secondary);
  cursor: pointer;
  transition: color var(--transition-base);

  &:hover {
    color: var(--primary-color);
  }

  &.is-uploader {
    color: var(--primary-color);
  }
}

.up-badge {
  display: inline-flex;
  align-items: center;
  padding: 0 var(--space-1);
  font-size: 10px;
  font-weight: var(--font-weight-medium);
  color: var(--text-white);
  background: var(--primary-gradient);
  border-radius: var(--radius-xs);
}

/* AI Badges */
.ai-badges {
  display: flex;
  gap: var(--space-1);
}

.ai-badge {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 0 var(--space-1);
  font-size: 10px;
  border-radius: var(--radius-xs);

  .badge-icon {
    font-style: normal;
  }

  &.premium {
    color: #B8860B;
    background: linear-gradient(135deg, #FFF8DC 0%, #FFE4B5 100%);
    border: 1px solid #FFD700;
  }

  &.normal {
    color: var(--text-tertiary);
    background: var(--bg-gray-1);
  }
}

/* Comment Text */
.comment-text {
  font-size: var(--font-size-base);
  color: var(--text-primary);
  line-height: var(--line-height-relaxed);
  margin: 0 0 var(--space-2);
  white-space: pre-wrap;
  word-break: break-word;
}

/* Action Row */
.action-row {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
}

.publish-time {
  color: var(--text-quaternary);
}

.action-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-1) var(--space-2);
  background: transparent;
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  color: var(--text-tertiary);
  transition: all var(--transition-base);

  .btn-icon {
    font-size: var(--font-size-sm);
    opacity: 0.7;
    transition: opacity var(--transition-base);
  }

  .btn-text {
    font-size: var(--font-size-xs);
  }

  &:hover {
    background: var(--bg-gray-1);
    color: var(--text-secondary);

    .btn-icon {
      opacity: 1;
    }
  }

  &.active {
    color: var(--primary-color);

    .btn-icon {
      opacity: 1;
    }
  }

  &.like-btn.active {
    color: var(--primary-color);
    
    .like-icon.is-liked {
      color: var(--primary-color);
      transform: rotate(-15deg) scale(1.1);
    }
  }
  
  .like-icon {
    transition: transform 0.2s, color 0.2s;
    &.is-liked {
      color: var(--primary-color);
      transform: rotate(-15deg) scale(1.1);
    }
  }
}

/* Reply Input */
.reply-input-wrap {
  margin-top: var(--space-3);
  padding-left: var(--space-2);
  border-left: 2px solid var(--primary-light);
}

/* Replies Container */
.replies-container {
  margin-top: var(--space-3);
  padding: var(--space-3);
  background: var(--bg-gray-1);
  border-radius: var(--radius-md);
}

.reply-item {
  display: flex;
  gap: var(--space-2);
  padding: var(--space-2) 0;

  &:not(:last-child) {
    border-bottom: 1px solid var(--border-light);
  }
}

.reply-avatar {
  width: 24px;
  height: 24px;
  border-radius: var(--radius-circle);
  object-fit: cover;
  flex-shrink: 0;
}

.reply-content {
  flex: 1;
  min-width: 0;
}

.reply-header {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  margin-bottom: var(--space-1);
}

.reply-username {
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-medium);
  color: var(--text-secondary);
  cursor: pointer;

  &:hover {
    color: var(--primary-color);
  }
}

.reply-ai-tag {
  font-size: 10px;
  color: var(--text-quaternary);
  background: var(--bg-gray-2);
  padding: 0 4px;
  border-radius: var(--radius-xs);
}

.reply-text {
  font-size: var(--font-size-sm);
  color: var(--text-primary);
  line-height: var(--line-height-normal);
  margin: 0 0 var(--space-1);
  word-break: break-word;
}

.reply-footer {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  font-size: var(--font-size-xs);
  color: var(--text-quaternary);
}

.reply-action {
  background: none;
  border: none;
  color: var(--text-tertiary);
  cursor: pointer;
  padding: 0;
  font-size: inherit;

  &:hover {
    color: var(--primary-color);
  }
}

.reply-time {
  color: var(--text-quaternary);
}

/* Show More Replies */
.show-more-replies {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  margin-top: var(--space-2);
  padding: var(--space-1) 0;
  background: none;
  border: none;
  font-size: var(--font-size-xs);
  color: var(--secondary-color);
  cursor: pointer;
  transition: color var(--transition-base);

  .arrow {
    font-size: 10px;
    font-style: normal;
    transition: transform var(--transition-base);
  }

  &:hover {
    color: var(--secondary-hover);

    .arrow {
      transform: translateY(2px);
    }
  }
}

/* Transitions */
.expand-enter-active,
.expand-leave-active {
  transition: all var(--transition-base);
  overflow: hidden;
}

.expand-enter-from,
.expand-leave-to {
  opacity: 0;
  max-height: 0;
}

.expand-enter-to,
.expand-leave-from {
  max-height: 200px;
}
</style>
