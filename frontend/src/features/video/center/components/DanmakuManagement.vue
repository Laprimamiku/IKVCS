<template>
  <div class="danmaku-management">
    <div class="toolbar">
      <div class="toolbar-left">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索弹幕内容"
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
        <el-button type="primary" @click="loadDanmakus">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
    </div>

    <div class="danmaku-list">
      <div v-if="loading" class="loading-state">
        <el-skeleton :rows="5" animated />
      </div>
      <div v-else-if="filteredDanmakus.length === 0" class="empty-state">
        <el-empty description="暂无弹幕" />
      </div>
      <div v-else>
        <div
          v-for="danmaku in filteredDanmakus"
          :key="danmaku.id"
          class="danmaku-item"
        >
          <div class="danmaku-header">
            <div class="user-info">
              <el-avatar :size="32" :src="danmaku.user?.avatar || '/default-avatar.png'">
                <el-icon><User /></el-icon>
              </el-avatar>
              <div class="user-details">
                <span class="username">{{ danmaku.user?.nickname || danmaku.user?.username || "匿名用户" }}</span>
                <span class="danmaku-time">{{ formatTime(danmaku.video_time) }} · {{ formatDate(danmaku.created_at) }}</span>
              </div>
            </div>
            <div class="danmaku-actions">
              <el-tag v-if="danmaku.is_highlight" type="success" size="small">
                优质弹幕
              </el-tag>
              <span class="danmaku-color" :style="{ background: danmaku.color }"></span>
              <el-button
                v-if="!danmaku.is_deleted"
                type="danger"
                size="small"
                @click="handleDelete(danmaku.id)"
              >
                删除
              </el-button>
              <el-button
                v-else
                type="success"
                size="small"
                @click="handleRestore(danmaku.id)"
              >
                恢复
              </el-button>
            </div>
          </div>
          <div class="danmaku-content" :class="{ deleted: danmaku.is_deleted }">
            {{ danmaku.content }}
          </div>
          <div class="danmaku-footer">
            <span class="danmaku-stats">
              <el-icon><CircleCheckFilled /></el-icon>
              {{ danmaku.like_count || 0 }}
            </span>
            <span v-if="danmaku.ai_score !== null && danmaku.ai_score !== undefined" class="danmaku-stats">
              AI评分: {{ danmaku.ai_score }}
            </span>
            <el-tag 
              v-if="danmaku.ai_category && danmaku.ai_category !== '普通'" 
              :type="getCategoryType(danmaku.ai_category)" 
              size="small"
            >
              {{ danmaku.ai_category }}
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
        @current-change="loadDanmakus"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Search, Refresh, User, CircleCheckFilled } from "@element-plus/icons-vue";
import { getManageDanmakus, deleteDanmaku, restoreDanmaku } from "@/features/video/center/api/interaction.api";
import { formatDate } from "@/shared/utils/formatters";

const props = defineProps<{
  videoId: number;
}>();

const loading = ref(false);
const danmakus = ref<any[]>([]);
const searchKeyword = ref("");
const filterStatus = ref("all");
const currentPage = ref(1);
const pageSize = ref(20);
const total = ref(0);

const filteredDanmakus = computed(() => {
  let result = danmakus.value;

  if (searchKeyword.value) {
    result = result.filter((d) =>
      d.content.toLowerCase().includes(searchKeyword.value.toLowerCase())
    );
  }

  // 基于 AI 评分筛选
  if (filterStatus.value !== "all") {
    result = result.filter((d) => {
      const score = d.ai_score;
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

const formatTime = (seconds: number) => {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
};

const loadDanmakus = async () => {
  loading.value = true;
  try {
    const response = await getManageDanmakus(props.videoId);
    if (response.success && response.data) {
      danmakus.value = Array.isArray(response.data) ? response.data : [];
      total.value = danmakus.value.length;
    } else {
      danmakus.value = [];
      total.value = 0;
    }
  } catch (error) {
    console.error("加载弹幕失败:", error);
    ElMessage.error("加载弹幕失败");
    danmakus.value = [];
    total.value = 0;
  } finally {
    loading.value = false;
  }
};

const handleDelete = async (danmakuId: number) => {
  try {
    await ElMessageBox.confirm("确定要删除这条弹幕吗？", "提示", {
      confirmButtonText: "确定",
      cancelButtonText: "取消",
      type: "warning",
    });
    await deleteDanmaku(props.videoId, danmakuId);
    ElMessage.success("删除成功");
    loadDanmakus();
  } catch (error: any) {
    if (error !== "cancel") {
      console.error("删除弹幕失败:", error);
      ElMessage.error("删除弹幕失败");
    }
  }
};

const handleRestore = async (danmakuId: number) => {
  try {
    await restoreDanmaku(props.videoId, danmakuId);
    ElMessage.success("恢复成功");
    loadDanmakus();
  } catch (error: any) {
    console.error("恢复弹幕失败:", error);
    ElMessage.error("恢复弹幕失败");
  }
};

const getCategoryType = (category: string): string => {
  const categoryMap: Record<string, string> = {
    "优质": "success",
    "普通": "info",
    "低价值": "warning",
    "违规": "danger",
    "疑似违规": "warning",
  };
  return categoryMap[category] || "info";
};

watch(() => props.videoId, () => {
  currentPage.value = 1;
  loadDanmakus();
}, { immediate: true });
</script>

<style lang="scss" scoped>
.danmaku-management {
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

.danmaku-list {
  min-height: 400px;
}

.danmaku-item {
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

.danmaku-header {
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
    
    .danmaku-time {
      font-size: var(--font-size-xs);
      color: var(--text-tertiary);
    }
  }
}

.danmaku-actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  
  .danmaku-color {
    width: 20px;
    height: 20px;
    border-radius: var(--radius-circle);
    border: 1px solid var(--border-color);
  }
}

.danmaku-content {
  font-size: var(--font-size-base);
  color: var(--text-primary);
  line-height: 1.6;
  margin-bottom: var(--space-2);
  
  &.deleted {
    color: var(--text-tertiary);
    text-decoration: line-through;
  }
}

.danmaku-footer {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  
  .danmaku-stats {
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
