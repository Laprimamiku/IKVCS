<template>
  <div class="video-comment-section">
    <div class="section-header">
      <h3 class="title">
        评论 <span>({{ total }})</span>
      </h3>

      <div class="tabs">
        <span
          class="tab-item"
          :class="{ active: sortBy === 'hot' }"
          @click="handleSortChange('hot')"
        >
          最热(AI推荐)
        </span>
        <span class="divider">|</span>
        <span
          class="tab-item"
          :class="{ active: sortBy === 'new' }"
          @click="handleSortChange('new')"
        >
          最新
        </span>
      </div>
    </div>

    <CommentInput
      :loading="submitting"
      placeholder="发一条友善的评论"
      @submit="handleCreateComment"
    />

    <div class="comment-list" v-loading="loading">
      <VideoCommentItem
        v-for="item in commentList"
        :key="item.id"
        :comment="item"
        :uploader-id="uploaderId"
        @reply="handleReplyComment"
      />

      <el-empty
        v-if="!loading && commentList.length === 0"
        description="还没有评论，快来抢沙发~"
      />

      <div class="load-more" v-if="hasMore">
        <el-button link @click="loadMore">查看更多评论</el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from "vue";
import { ElMessage } from "element-plus";
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

// 状态
const loading = ref(false);
const submitting = ref(false);
const commentList = ref<Comment[]>([]);
const total = ref(0);
const sortBy = ref<"new" | "hot">("hot"); // 默认最热
const page = ref(1);
const pageSize = 20;
const hasMore = ref(false);

// 加载评论
const fetchComments = async (reset = false) => {
  if (reset) {
    page.value = 1;
    loading.value = true;
  }

  try {
    const res = await getComments(props.videoId, {
      page: page.value,
      page_size: pageSize,
      sort_by: sortBy.value,
    });

    if (res.success) {
      // [修复点 1]: 从 res.data 中解构，而不是直接从 res 解构
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
  }
};

// 切换排序
const handleSortChange = (type: "new" | "hot") => {
  if (sortBy.value === type) return;
  sortBy.value = type;
  fetchComments(true);
};

// 发表评论（根评论）
const handleCreateComment = async (content: string) => {
  submitting.value = true;
  try {
    const res = await createComment(props.videoId, { content });
    if (res.success) {
      ElMessage.success("评论发表成功");
      // [修复点 2]: 使用 res.data (真实的 Comment 对象) 而不是 res
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

// 回复评论
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
        // [修复点 3]: 使用 res.data
        parent.replies.push(res.data);
        // 可选：更新回复数显示
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

// 监听 VideoID 变化（切换视频时）
watch(
  () => props.videoId,
  () => {
    fetchComments(true);
  },
  { immediate: true }
);
</script>

<style scoped lang="scss">
.video-comment-section {
  margin-top: 24px;
  padding: 0;

  .section-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 20px;

    .title {
      font-size: 18px;
      font-weight: 600;
      color: var(--text-primary);
      margin: 0;

      span {
        font-size: 14px;
        color: var(--text-tertiary);
        margin-left: 6px;
        font-weight: normal;
      }
    }

    .tabs {
      display: flex;
      align-items: center;
      font-size: 14px;
      color: var(--text-secondary);

      .tab-item {
        cursor: pointer;
        padding: 4px 8px;
        border-radius: var(--radius-sm);
        transition: all 0.2s;

        &:hover {
          color: var(--primary-color);
          background: var(--primary-light);
        }

        &.active {
          color: var(--primary-color);
          font-weight: 500;
          background: var(--primary-light);
        }
      }

      .divider {
        margin: 0 8px;
        color: var(--border-light);
      }
    }
  }

  .load-more {
    text-align: center;
    padding: 20px 0;

    :deep(.el-button) {
      color: var(--text-secondary);
      font-size: 14px;

      &:hover {
        color: var(--primary-color);
      }
    }
  }
}
</style>
