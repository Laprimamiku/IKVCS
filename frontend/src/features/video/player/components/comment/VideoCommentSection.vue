<template>
  <div class="bili-comment-section">
    <!-- Section Header -->
    <div class="comment-header">
      <div class="header-left">
        <h3 class="comment-title">评论</h3>
        <span class="comment-count">{{ total }}</span>
      </div>

      <div class="header-right">
        <!-- AI Purification Toggle -->
        <div class="ai-purify-toggle">
          <span class="toggle-label">
            <el-icon><MagicStick /></el-icon> 一键净化
          </span>
          <el-switch
            v-model="isPurified"
            size="small"
            style="--el-switch-on-color: #13ce66"
          />
        </div>

        <div class="sort-tabs">
          <span
            class="sort-tab"
            :class="{ active: sortBy === 'hot' }"
            @click="handleSortChange('hot')"
          >
            <el-icon class="tab-icon"><TrendCharts /></el-icon>
            最热
          </span>
          <span class="sort-divider"></span>
          <span
            class="sort-tab"
            :class="{ active: sortBy === 'new' }"
            @click="handleSortChange('new')"
          >
            <el-icon class="tab-icon"><Clock /></el-icon>
            最新
          </span>
        </div>
      </div>
    </div>

    <!-- Purification Hint -->
    <transition name="el-fade-in-linear">
      <div v-if="isPurified && purifiedCount > 0" class="purify-hint-bar">
        <el-icon><sugar /></el-icon>
        <span>AI 已为您净化 {{ purifiedCount }} 条低质/引战评论</span>
      </div>
    </transition>

    <!-- Comment Input -->
    <CommentInput
      :loading="submitting"
      placeholder="发一条友善的评论吧~"
      @submit="handleCreateComment"
    />

    <!-- Comment List -->
    <div class="comment-list" v-loading="loading">
      <transition-group name="comment-fade">
        <VideoCommentItem
          v-for="item in visibleComments"
          :key="item.id"
          :comment="item"
          :uploader-id="uploaderId"
          @reply="handleReplyComment"
        />
      </transition-group>

      <!-- Empty State -->
      <div v-if="!loading && visibleComments.length === 0" class="empty-state">
        <el-icon class="empty-icon" :size="48"><ChatDotRound /></el-icon>
        <p class="empty-text">
          {{ isPurified && commentList.length > 0 ? '评论区已净化，暂无可见内容' : '还没有评论，快来抢沙发吧~' }}
        </p>
      </div>

      <!-- Load More -->
      <div class="load-more-wrap" v-if="hasMore && !loading">
        <button class="load-more-btn" @click="loadMore">
          <span>查看更多评论</span>
          <i class="arrow-icon">↓</i>
        </button>
      </div>

      <!-- Loading More Indicator -->
      <div v-if="loadingMore" class="loading-more">
        <i class="loading-spinner"></i>
        <span>加载中...</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed } from "vue";
import { ElMessage } from "element-plus";
import { MagicStick, Sugar, TrendCharts, Clock, ChatDotRound } from "@element-plus/icons-vue";
import type { Comment } from "@/shared/types/entity";
import {
  getComments,
  createComment,
} from "@/features/video/player/api/comment.api";
import CommentInput from "./CommentInput.vue";
import VideoCommentItem from "./VideoCommentItem.vue";

const props = defineProps<{
  videoId: number;
  uploaderId?: number;
}>();

// State
const loading = ref(false);
const loadingMore = ref(false);
const submitting = ref(false);
const commentList = ref<Comment[]>([]);
const total = ref(0);
const sortBy = ref<"new" | "hot">("hot");
const page = ref(1);
const pageSize = 20;
const hasMore = ref(false);

// AI Purification
const isPurified = ref(false);

const visibleComments = computed(() => {
  if (!isPurified.value) return commentList.value;
  
  return commentList.value.filter(comment => {
    // Filter logic: Score < 30 or explicitly flagged as inappropriate
    // Default score to 100 if missing (assume innocent until proven guilty)
    const score = comment.ai_score ?? 100; 
    const isBad = score < 30 || (comment as any).is_inappropriate === true;
    return !isBad;
  });
});

const purifiedCount = computed(() => {
  return commentList.value.length - visibleComments.value.length;
});

// Fetch comments
const fetchComments = async (reset = false) => {
  if (reset) {
    page.value = 1;
    loading.value = true;
  } else {
    loadingMore.value = true;
  }

  try {
    const res = await getComments(props.videoId, {
      page: page.value,
      page_size: pageSize,
      sort_by: sortBy.value,
    });

    if (res.success) {
      const { items, total: totalCount } = res.data;

      if (reset) {
        commentList.value = items;
      } else {
        commentList.value.push(...items);
      }
      total.value = totalCount;
      hasMore.value = commentList.value.length < totalCount;
      page.value++;
    }
  } catch (error) {
    console.error("Failed to load comments:", error);
  } finally {
    loading.value = false;
    loadingMore.value = false;
  }
};

// Sort change handler
const handleSortChange = (type: "new" | "hot") => {
  if (sortBy.value === type) return;
  sortBy.value = type;
  fetchComments(true);
};

// Create root comment
const handleCreateComment = async (content: string) => {
  submitting.value = true;
  try {
    const res = await createComment(props.videoId, { content });
    if (res.success) {
      ElMessage.success("评论发表成功");
      if (sortBy.value === "new") {
        commentList.value.unshift(res.data);
        total.value++;
      } else {
        fetchComments(true);
      }
    }
  } finally {
    submitting.value = false;
  }
};

// Reply to comment
const handleReplyComment = async (content: string, parentId: number) => {
  try {
    const res = await createComment(props.videoId, {
      content,
      parent_id: parentId,
    });
    if (res.success) {
      ElMessage.success("回复成功");
      const parent = commentList.value.find((c) => c.id === parentId);
      if (parent) {
        if (!parent.replies) parent.replies = [];
        parent.replies.push(res.data);
        parent.reply_count = (parent.reply_count || 0) + 1;
      }
    }
  } catch (e) {
    console.error(e);
  }
};

const loadMore = () => {
  fetchComments(false);
};

// Watch videoId changes
watch(
  () => props.videoId,
  () => {
    fetchComments(true);
  },
  { immediate: true }
);
</script>

<style scoped lang="scss">
.bili-comment-section {
  margin-top: var(--space-6);
  padding: 0;
}

/* Header */
.comment-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-5);
  padding-bottom: var(--space-4);
  border-bottom: 1px solid var(--border-light);

  .header-left {
    display: flex;
    align-items: baseline;
    gap: var(--space-2);
  }

  .comment-title {
    font-size: var(--font-size-xl);
    font-weight: var(--font-weight-semibold);
    color: var(--text-primary);
    margin: 0;
  }

  .comment-count {
    font-size: var(--font-size-sm);
    color: var(--text-tertiary);
  }
}

.header-right {
  display: flex;
  align-items: center;
  gap: 20px;
}

/* AI Purification Toggle */
.ai-purify-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  
  .toggle-label {
    font-size: 13px;
    color: #606266;
    display: flex;
    align-items: center;
    gap: 4px;
    
    .el-icon {
      color: #00aeec;
    }
  }
}

/* Purification Hint Bar */
.purify-hint-bar {
  margin-bottom: 16px;
  background: #f0f9eb;
  color: #67c23a;
  padding: 8px 16px;
  border-radius: 4px;
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
  border: 1px solid #e1f3d8;
  
  .el-icon {
    font-size: 16px;
  }
}

/* Sort Tabs */
.sort-tabs {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  background: var(--bg-gray-1);
  padding: var(--space-1);
  border-radius: var(--radius-round);
}

.sort-tab {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-1) var(--space-3);
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  cursor: pointer;
  border-radius: var(--radius-round);
  transition: all var(--transition-base);

  .tab-icon {
    font-size: var(--font-size-xs);
    font-style: normal;
  }

  &:hover {
    color: var(--text-primary);
  }

  &.active {
    background: var(--bg-white);
    color: var(--primary-color);
    font-weight: var(--font-weight-medium);
    box-shadow: var(--shadow-sm);
  }
}

.sort-divider {
  width: 1px;
  height: 12px;
  background: var(--border-color);
}

/* Comment List */
.comment-list {
  min-height: 200px;
}

/* Empty State */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-12) 0;
  color: var(--text-tertiary);

  .empty-icon {
    font-size: 48px;
    margin-bottom: var(--space-4);
    opacity: 0.5;
  }

  .empty-text {
    font-size: var(--font-size-base);
    margin: 0;
  }
}

/* Load More */
.load-more-wrap {
  display: flex;
  justify-content: center;
  padding: var(--space-6) 0;
}

.load-more-btn {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-6);
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  background: var(--bg-gray-1);
  border: none;
  border-radius: var(--radius-round);
  cursor: pointer;
  transition: all var(--transition-base);

  .arrow-icon {
    font-style: normal;
    transition: transform var(--transition-base);
  }

  &:hover {
    color: var(--primary-color);
    background: var(--primary-light);

    .arrow-icon {
      transform: translateY(2px);
    }
  }
}

/* Loading More */
.loading-more {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  padding: var(--space-4) 0;
  color: var(--text-tertiary);
  font-size: var(--font-size-sm);
}

.loading-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid var(--border-color);
  border-top-color: var(--primary-color);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* Transition */
.comment-fade-enter-active,
.comment-fade-leave-active {
  transition: all var(--transition-slow);
}

.comment-fade-enter-from {
  opacity: 0;
  transform: translateY(-10px);
}

.comment-fade-leave-to {
  opacity: 0;
  transform: translateY(10px);
}
</style>
