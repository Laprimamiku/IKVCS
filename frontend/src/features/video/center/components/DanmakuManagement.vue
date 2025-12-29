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
        <el-select v-model="filterStatus" placeholder="筛选状态" style="width: 150px; margin-left: 12px;">
          <el-option label="全部" value="all" />
          <el-option label="已审核" value="approved" />
          <el-option label="待审核" value="pending" />
          <el-option label="已删除" value="deleted" />
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
                <span class="username">{{ danmaku.user?.nickname || "匿名用户" }}</span>
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
            <span v-if="danmaku.ai_score" class="danmaku-stats">
              AI评分: {{ danmaku.ai_score }}
            </span>
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
import { ref, computed, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Search, Refresh, User, CircleCheckFilled } from "@element-plus/icons-vue";
import { getDanmakus } from "@/features/video/player/api/danmaku.api";
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

  if (filterStatus.value === "approved") {
    result = result.filter((d) => !d.is_deleted);
  } else if (filterStatus.value === "deleted") {
    result = result.filter((d) => d.is_deleted);
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
    const response = await getDanmakus(props.videoId);
    if (response.data) {
      danmakus.value = response.data || [];
      total.value = danmakus.value.length;
    }
  } catch (error) {
    console.error("加载弹幕失败:", error);
    ElMessage.error("加载弹幕失败");
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
    // TODO: 实现删除弹幕 API
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
  // TODO: 实现恢复弹幕功能
  ElMessage.info("恢复功能开发中");
};

onMounted(() => {
  loadDanmakus();
});
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

