<template>
  <div class="comment-management">
    <div class="toolbar">
      <div class="toolbar-left">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索评论内容"
          clearable
          style="width: 300px;"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-select v-model="filterStatus" placeholder="筛选评分" style="width: 150px; margin-left: 12px;">
          <el-option label="全部" value="all" />
          <el-option label="优秀 (90-100分)" value="excellent" />
          <el-option label="良好 (70-89分)" value="good" />
          <el-option label="一般 (60-79分)" value="average" />
          <el-option label="较差 (0-59分)" value="poor" />
        </el-select>
      </div>
      <div class="toolbar-right">
        <el-button type="primary" @click="loadComments">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
    </div>

    <div class="comment-list">
      <div v-if="loading" class="loading-state">
        <el-skeleton :rows="5" animated />
      </div>
      <div v-else-if="filteredComments.length === 0" class="empty-state">
        <el-empty description="暂无评论" />
      </div>
      <div v-else>
        <div
          v-for="comment in filteredComments"
          :key="comment.id"
          class="comment-item"
        >
          <div class="comment-header">
            <div class="user-info">
              <el-avatar :size="32" :src="comment.user?.avatar || '/default-avatar.png'">
                <el-icon><User /></el-icon>
              </el-avatar>
              <div class="user-details">
                <span class="username">{{ comment.user?.nickname || "匿名用户" }}</span>
                <span class="comment-time">{{ formatTime(comment.created_at) }}</span>
              </div>
            </div>
            <div class="comment-actions">
              <el-button
                v-if="!comment.is_deleted"
                type="danger"
                size="small"
                @click="handleDelete(comment.id)"
              >
                删除
              </el-button>
              <el-button
                v-else
                type="success"
                size="small"
                @click="handleRestore(comment.id)"
              >
                恢复
              </el-button>
            </div>
          </div>
          <div class="comment-content" :class="{ deleted: comment.is_deleted }">
            {{ comment.content }}
          </div>
          <div class="comment-footer">
            <span class="comment-stats">
              <el-icon><CircleCheckFilled /></el-icon>
              {{ comment.like_count || 0 }}
            </span>
            <span class="comment-stats">
              <el-icon><ChatDotRound /></el-icon>
              {{ comment.reply_count || 0 }} 条回复
            </span>
            <span v-if="comment.ai_score !== null && comment.ai_score !== undefined" class="comment-stats">
              AI评分: {{ comment.ai_score }}
            </span>
            <el-tag 
              v-if="comment.ai_label && comment.ai_label !== '普通'" 
              :type="getLabelType(comment.ai_label)" 
              size="small"
            >
              {{ comment.ai_label }}
            </el-tag>
          </div>
        </div>
      </div>
    </div>

    <div v-if="total > 0" class="pagination">
      <el-pagination
        v-model:current-page="currentPage"
        :page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next"
        @current-change="loadComments"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Search, Refresh, User, CircleCheckFilled, ChatDotRound } from "@element-plus/icons-vue";
import { getComments, deleteComment } from "@/features/video/player/api/comment.api";
import { formatDate } from "@/shared/utils/formatters";

const props = defineProps<{
  videoId: number;
}>();

const loading = ref(false);
const comments = ref<any[]>([]);
const searchKeyword = ref("");
const filterStatus = ref("all");
const currentPage = ref(1);
const pageSize = ref(20);
const total = ref(0);

const filteredComments = computed(() => {
  let result = comments.value;

  if (searchKeyword.value) {
    result = result.filter((c) =>
      c.content.toLowerCase().includes(searchKeyword.value.toLowerCase())
    );
  }

  // 基于 AI 评分筛选
  if (filterStatus.value !== "all") {
    result = result.filter((c) => {
      const score = c.ai_score;
      if (score === null || score === undefined) return false;
      
      switch (filterStatus.value) {
        case "excellent":
          return score >= 90 && score <= 100;
        case "good":
          return score >= 70 && score < 90;
        case "average":
          return score >= 60 && score < 70;
        case "poor":
          return score < 60;
        default:
          return true;
      }
    });
  }

  return result;
});

const formatTime = (dateStr: string) => {
  return formatDate(dateStr);
};

const loadComments = async () => {
  loading.value = true;
  try {
    const response = await getComments(props.videoId, {
      page: currentPage.value,
      page_size: pageSize.value,
      sort_by: 'new'
    });
    if (response.success && response.data) {
      comments.value = response.data.items || [];
      total.value = response.data.total || 0;
    } else {
      comments.value = [];
      total.value = 0;
    }
  } catch (error) {
    console.error("加载评论失败:", error);
    ElMessage.error("加载评论失败");
    comments.value = [];
    total.value = 0;
  } finally {
    loading.value = false;
  }
};

const handleDelete = async (commentId: number) => {
  try {
    await ElMessageBox.confirm("确定要删除这条评论吗？", "提示", {
      confirmButtonText: "确定",
      cancelButtonText: "取消",
      type: "warning",
    });
    await deleteComment(commentId);
    ElMessage.success("删除成功");
    loadComments();
  } catch (error: any) {
    if (error !== "cancel") {
      console.error("删除评论失败:", error);
      ElMessage.error("删除评论失败");
    }
  }
};

const handleRestore = async (commentId: number) => {
  // TODO: 实现恢复评论功能
  ElMessage.info("恢复功能开发中");
};

const getLabelType = (label: string): string => {
  const labelMap: Record<string, string> = {
    "优质": "success",
    "普通": "info",
    "低价值": "warning",
    "违规": "danger",
    "疑似违规": "warning",
  };
  return labelMap[label] || "info";
};

onMounted(() => {
  loadComments();
});
</script>

<style lang="scss" scoped>
.comment-management {
  width: 100%;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-4);
  
  .toolbar-left {
    display: flex;
    align-items: center;
  }
}

.comment-list {
  min-height: 400px;
}

.comment-item {
  padding: var(--space-4);
  border-bottom: 1px solid var(--border-light);
  transition: background var(--transition-base);
  
  &:hover {
    background: var(--bg-hover);
  }
  
  &:last-child {
    border-bottom: none;
  }
}

.comment-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-2);
}

.user-info {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  
  .user-details {
    display: flex;
    flex-direction: column;
    gap: var(--space-1);
    
    .username {
      font-size: var(--font-size-sm);
      font-weight: var(--font-weight-medium);
      color: var(--text-primary);
    }
    
    .comment-time {
      font-size: var(--font-size-xs);
      color: var(--text-tertiary);
    }
  }
}

.comment-actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.comment-content {
  font-size: var(--font-size-base);
  color: var(--text-primary);
  line-height: 1.6;
  margin-bottom: var(--space-2);
  
  &.deleted {
    color: var(--text-tertiary);
    text-decoration: line-through;
  }
}

.comment-footer {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  
  .comment-stats {
    display: flex;
    align-items: center;
    gap: var(--space-1);
    font-size: var(--font-size-sm);
    color: var(--text-secondary);
  }
}

.pagination {
  margin-top: var(--space-6);
  display: flex;
  justify-content: center;
}
</style>

