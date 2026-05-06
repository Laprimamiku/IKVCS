<template>
  <div class="bili-comment-item">
    <!-- User Avatar -->
    <div class="avatar-col">
      <el-avatar :src="comment.user.avatar" :size="48" class="user-avatar">
        {{ comment.user.nickname?.charAt(0).toUpperCase() || 'U' }}
      </el-avatar>
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
          <ThumbsUpIcon :size="16" :is-liked="localIsLiked" class="btn-icon like-icon" />
          <span class="btn-text">{{ localLikeCount || '' }}</span>
        </button>

        <!-- Delete Button (only for owner) -->
        <button
          v-if="canDeleteComment"
          class="action-btn delete-btn"
          @click="handleDeleteComment(comment.id)"
        >
          <el-icon class="btn-icon"><Delete /></el-icon>
          <span class="btn-text">删除</span>
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
        v-if="(comment.reply_count || 0) > 0" 
        class="replies-container"
      >
        <div v-if="replyLoading" class="reply-loading">加载回复中...</div>
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
              <button
                v-if="canDeleteReply(reply)"
                class="reply-action delete-reply"
                @click="handleDeleteComment(reply.id)"
              >
                删除
              </button>
            </div>
          </div>
        </div>

        <div v-if="replyTotal > replyPageSize" class="reply-pagination">
          <button
            class="reply-page-btn nav"
            :disabled="replyCurrentPage <= 1"
            @click="handleReplyPageChange(replyCurrentPage - 1)"
          >
            上一页
          </button>
          <button
            v-for="item in replyVisiblePageItems"
            :key="String(item)"
            class="reply-page-btn"
            :class="{ active: item === replyCurrentPage, ellipsis: typeof item !== 'number' }"
            :disabled="typeof item !== 'number'"
            @click="typeof item === 'number' && handleReplyPageChange(item)"
          >
            {{ typeof item === 'number' ? item : '...' }}
          </button>
          <button
            class="reply-page-btn nav"
            :disabled="replyCurrentPage >= replyTotalPages"
            @click="handleReplyPageChange(replyCurrentPage + 1)"
          >
            下一页
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Star, ChatDotRound, Warning, Delete } from "@element-plus/icons-vue";
import ThumbsUpIcon from "@/shared/components/icons/ThumbsUpIcon.vue";
import type { Comment } from "@/shared/types/entity";
import { toggleCommentLike, getReplies } from "@/features/video/player/api/comment.api";
import { deleteComment } from "@/features/video/player/api/comment.api";
import { createReport } from "@/features/video/player/api/report.api";
import { useUserStore } from "@/shared/stores/user";
import CommentInput from "./CommentInput.vue";

const props = defineProps<{
  comment: Comment;
  uploaderId?: number;
}>();

const emit = defineEmits<{
  (e: "reply", content: string, parentId: number, replyToUserId?: number | null): Promise<void>;
  (e: "deleted", commentId: number): void;
}>();

const userStore = useUserStore();

// Reply state
const showReplyBox = ref(false);
const submitting = ref(false);
const replyToUser = ref<{ id: number; nickname: string } | null>(null); // 回复目标用户
const replyCurrentPage = ref(1);
const replyPageSize = 3;
const replyLoading = ref(false);
const replyItems = ref<Comment[]>([]);
const replyTotal = ref(0);

// Like state (optimistic update)
const localIsLiked = ref(!!props.comment.is_liked);
const localLikeCount = ref(props.comment.like_count || 0);

// Computed
const isUploader = computed(() => props.comment.user_id === props.uploaderId);
const canDeleteComment = computed(() => userStore.userInfo?.id === props.comment.user_id);
const canDeleteReply = (reply: Comment) => userStore.userInfo?.id === reply.user_id;

const displayedReplies = computed(() => replyItems.value);

const replyTotalPages = computed(() => {
  return Math.max(1, Math.ceil(replyTotal.value / replyPageSize));
});

const replyVisiblePageItems = computed<(number | string)[]>(() => {
  const pageCount = replyTotalPages.value;
  const page = replyCurrentPage.value;

  if (pageCount <= 7) {
    return Array.from({ length: pageCount }, (_, index) => index + 1);
  }

  if (page <= 4) {
    return [1, 2, 3, 4, 5, "ellipsis-right", pageCount];
  }

  if (page >= pageCount - 3) {
    return [1, "ellipsis-left", pageCount - 4, pageCount - 3, pageCount - 2, pageCount - 1, pageCount];
  }

  return [1, "ellipsis-left", page - 1, page, page + 1, "ellipsis-right", pageCount];
});

const handleReplyPageChange = (page: number) => {
  if (page < 1 || page > replyTotalPages.value || page === replyCurrentPage.value) return;
  replyCurrentPage.value = page;
  loadReplies(page);
};

const loadReplies = async (page = 1) => {
  replyLoading.value = true;
  try {
    const res = await getReplies(props.comment.id, { page, page_size: replyPageSize });
    if (res.success && res.data) {
      replyItems.value = res.data.items || [];
      replyTotal.value = res.data.total || 0;
      replyCurrentPage.value = res.data.page || page;
    }
  } catch (error) {
    console.error("加载回复失败:", error);
  } finally {
    replyLoading.value = false;
  }
};

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
    await loadReplies(1);
  } finally {
    submitting.value = false;
  }
};

watch(
  () => props.comment.id,
  () => {
    replyCurrentPage.value = 1;
    if ((props.comment.reply_count || 0) > 0) {
      loadReplies(1);
    } else {
      replyItems.value = [];
      replyTotal.value = 0;
    }
  },
  { immediate: true }
);

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

const handleDeleteComment = async (commentId: number) => {
  if (!userStore.isLoggedIn) {
    ElMessage.warning("请先登录");
    return;
  }

  try {
    await ElMessageBox.confirm("确认删除这条评论吗？", "删除评论", {
      confirmButtonText: "删除",
      cancelButtonText: "取消",
      type: "warning",
    });

    const res = await deleteComment(commentId);
    if (res.success) {
      ElMessage.success("评论已删除");
      if (commentId === props.comment.id) {
        emit("deleted", commentId);
      } else {
        replyItems.value = replyItems.value.filter((item) => item.id !== commentId);
        replyTotal.value = Math.max(0, replyTotal.value - 1);
      }
    } else {
      ElMessage.error(res.message || "删除失败");
    }
  } catch (error: unknown) {
    if (error !== "cancel") {
      ElMessage.error("删除失败");
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

.reply-pagination {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: var(--space-2);
}

.reply-loading {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  margin-bottom: var(--space-1);
}

.reply-page-btn {
  min-width: 28px;
  height: 24px;
  padding: 0 8px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  background: var(--bg-white);
  color: var(--text-secondary);
  font-size: var(--font-size-xs);
  cursor: pointer;

  &:hover:not(:disabled) {
    color: var(--primary-color);
    border-color: var(--primary-color);
  }

  &.active {
    color: var(--text-white);
    background: var(--primary-color);
    border-color: var(--primary-color);
  }

  &.ellipsis {
    cursor: default;
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
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
