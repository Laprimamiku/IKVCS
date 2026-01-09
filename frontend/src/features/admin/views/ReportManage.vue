<template>
  <div class="report-page">
    <div class="page-header">
      <h2>举报管理</h2>
    </div>

    <el-card shadow="never" class="table-card">
      <el-tabs v-model="currentStatus" @tab-change="handleTabChange" class="report-tabs">
        <el-tab-pane label="待处理" :name="0">
          <template #label>
            <span class="tab-label">
              <el-icon><Warning /></el-icon>
              <span>待处理</span>
              <el-badge v-if="pendingCount > 0" :value="pendingCount" class="tab-badge" />
            </span>
          </template>
        </el-tab-pane>
        <el-tab-pane label="已处理" :name="1">
          <template #label>
            <span class="tab-label">
              <el-icon><Check /></el-icon>
              <span>已处理</span>
            </span>
          </template>
        </el-tab-pane>
        <el-tab-pane label="已忽略" :name="2">
          <template #label>
            <span class="tab-label">
              <el-icon><Close /></el-icon>
              <span>已忽略</span>
            </span>
          </template>
        </el-tab-pane>
      </el-tabs>

      <el-table
        :data="reports"
        stripe
        v-loading="loading"
        empty-text="暂无数据"
        class="report-table"
      >
        <el-table-column label="被举报内容" min-width="280">
          <template #default="{ row }">
            <div class="content-cell">
              <div class="content-header">
                <el-tag
                  :type="getTypeTagType(row.target_type)"
                  size="small"
                  effect="dark"
                >
                  {{ getTypeText(row.target_type) }}
                </el-tag>
                <el-tag type="warning" size="small" style="margin-left: 8px;">
                  {{ row.reason }}
                </el-tag>
              </div>
              <div v-if="row.target_snapshot" class="target-info">
                <!-- 视频预览 -->
                <template v-if="row.target_type === 'VIDEO' && 'title' in row.target_snapshot">
                  <div class="target-title">
                    <el-icon><VideoPlay /></el-icon>
                    <span>{{ row.target_snapshot.title }}</span>
                  </div>
                  <div class="target-meta">
                    <span v-if="row.target_snapshot.uploader" class="meta-item">
                      <el-icon><User /></el-icon>
                      {{ row.target_snapshot.uploader.nickname || row.target_snapshot.uploader.username }}
                    </span>
                    <el-tag
                      :type="getStatusTagType(row.target_snapshot.status)"
                      size="small"
                    >
                      {{ getStatusText(row.target_snapshot.status) }}
                    </el-tag>
                  </div>
                </template>
                <!-- 评论预览 -->
                <template v-else-if="row.target_type === 'COMMENT' && 'content' in row.target_snapshot">
                  <div class="target-content">
                    <el-icon><ChatLineRound /></el-icon>
                    <span>{{ row.target_snapshot.content }}</span>
                  </div>
                  <div class="target-meta">
                    <span v-if="row.target_snapshot.user" class="meta-item">
                      <el-icon><User /></el-icon>
                      {{ row.target_snapshot.user.nickname || row.target_snapshot.user.username }}
                    </span>
                  </div>
                </template>
                <!-- 弹幕预览 -->
                <template v-else-if="row.target_type === 'DANMAKU' && 'content' in row.target_snapshot">
                  <div class="target-content">
                    <el-icon><ChatDotRound /></el-icon>
                    <span>{{ row.target_snapshot.content }}</span>
                  </div>
                  <div class="target-meta">
                    <span v-if="row.target_snapshot.user" class="meta-item">
                      <el-icon><User /></el-icon>
                      {{ row.target_snapshot.user.nickname || row.target_snapshot.user.username }}
                    </span>
                    <span class="meta-item">
                      <el-icon><Timer /></el-icon>
                      {{ formatVideoTime(row.target_snapshot.video_time) }}
                    </span>
                  </div>
                </template>
              </div>
              <div v-else class="target-missing">
                <el-icon><WarningFilled /></el-icon>
                <span>ID: {{ row.target_id }} (内容已删除)</span>
              </div>
              <div v-if="row.description" class="description-text">
                <el-icon><Document /></el-icon>
                <span>{{ row.description }}</span>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="举报信息" width="180">
          <template #default="{ row }">
            <div class="reporter-cell">
              <div class="reporter-info">
                <el-icon><User /></el-icon>
                <span>{{ row.reporter?.nickname || row.reporter?.username || '未知' }}</span>
              </div>
              <div class="time-info">
                <el-icon><Clock /></el-icon>
                <span>{{ formatDateTime(row.created_at) }}</span>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column v-if="currentStatus === 0" label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-dropdown trigger="click" @command="(cmd) => handleReport(row.id, cmd as any)">
              <el-button type="primary" size="small">
                处理<el-icon class="el-icon--right"><arrow-down /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <template v-if="row.target_type === 'VIDEO'">
                    <el-dropdown-item command="disable">
                      <el-icon><Remove /></el-icon>
                      下架视频
                    </el-dropdown-item>
                    <el-dropdown-item command="request_review">
                      <el-icon><Refresh /></el-icon>
                      请求复审
                    </el-dropdown-item>
                  </template>
                  <el-dropdown-item command="delete_target" divided>
                    <el-icon><Delete /></el-icon>
                    删除内容
                  </el-dropdown-item>
                  <el-dropdown-item command="ignore">
                    <el-icon><Close /></el-icon>
                    忽略举报
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
            <el-button
              v-if="row.admin_target_url"
              type="info"
              size="small"
              link
              @click="handleViewTarget(row.admin_target_url)"
              style="margin-left: 8px;"
            >
              <el-icon><View /></el-icon>
              查看
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-container" v-if="total > 0">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="loadData"
          @current-change="loadData"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  Warning,
  Check,
  Close,
  VideoPlay,
  User,
  View,
  ChatLineRound,
  ChatDotRound,
  Timer,
  WarningFilled,
  Clock,
  Remove,
  Refresh,
  Delete,
  Document,
  ArrowDown,
} from "@element-plus/icons-vue";
import { adminApi, type ReportItem } from "../api/admin.api";

const currentStatus = ref<number | string>(0);
const reports = ref<ReportItem[]>([]);
const loading = ref(false);
const currentPage = ref(1);
const pageSize = ref(20);
const total = ref(0);

const pendingCount = computed(() => {
  // 可以从统计数据中获取，这里暂时返回0
  return 0;
});

const statusMap: Record<number, string> = {
  0: "待处理",
  1: "已处理",
  2: "已忽略",
};

const loadData = async () => {
  loading.value = true;
  try {
    const res = await adminApi.getReports(Number(currentStatus.value), currentPage.value);
    if (res.success && res.data) {
      if (res.data.items && Array.isArray(res.data.items)) {
        reports.value = res.data.items;
        total.value = res.data.total || 0;
      } else if (Array.isArray(res.data)) {
        reports.value = res.data;
        total.value = res.data.length;
      } else {
        reports.value = [];
        total.value = 0;
      }
    } else {
      reports.value = [];
      total.value = 0;
    }
  } catch (e) {
    console.error('加载举报列表失败:', e);
    ElMessage.error('加载举报列表失败');
    reports.value = [];
    total.value = 0;
  } finally {
    loading.value = false;
  }
};

const handleTabChange = (name: string | number) => {
  currentStatus.value = name;
  currentPage.value = 1;
  loadData();
};

const handleReport = async (id: number, action: "delete_target" | "ignore" | "disable" | "request_review") => {
  const confirmTexts: Record<string, string> = {
    delete_target: "确认删除该违规内容吗？此操作不可逆（软删除）",
    ignore: "确认忽略该举报吗？",
    disable: "确认下架该视频吗？视频将暂时对用户不可见",
    request_review: "确认请求复审该视频吗？视频将重新进入审核流程"
  };
  const confirmText = confirmTexts[action] || "确认执行此操作吗？";
  
  try {
    await ElMessageBox.confirm(confirmText, "确认操作", {
      confirmButtonText: "确认",
      cancelButtonText: "取消",
      type: "warning",
    });

    loading.value = true;
    await adminApi.handleReport(id, action);
    ElMessage.success("操作成功");
    loadData(); // 刷新列表
  } catch (e: any) {
    if (e !== "cancel") {
      console.error("操作失败:", e);
      ElMessage.error("操作失败");
    }
  } finally {
    loading.value = false;
  }
};

const getStatusClass = (status: number): string => {
  const statusMap: Record<number, string> = {
    0: 'status-transcoding',
    1: 'status-reviewing',
    2: 'status-published',
    3: 'status-rejected',
    4: 'status-deleted'
  };
  return statusMap[status] || '';
};

const getStatusText = (status: number): string => {
  const statusMap: Record<number, string> = {
    0: '转码中',
    1: '审核中',
    2: '已发布',
    3: '已拒绝',
    4: '已删除'
  };
  return statusMap[status] || '未知';
};

const getStatusTagType = (status: number): string => {
  const typeMap: Record<number, string> = {
    0: 'info',
    1: 'warning',
    2: 'success',
    3: 'danger',
    4: 'info'
  };
  return typeMap[status] || 'info';
};

const getTypeTagType = (type: string): string => {
  const typeMap: Record<string, string> = {
    'VIDEO': 'primary',
    'COMMENT': 'success',
    'DANMAKU': 'danger'
  };
  return typeMap[type] || 'info';
};

const getTypeText = (type: string): string => {
  const typeMap: Record<string, string> = {
    'VIDEO': '视频',
    'COMMENT': '评论',
    'DANMAKU': '弹幕'
  };
  return typeMap[type] || type;
};

const handleViewTarget = (url: string) => {
  if (url) {
    window.open(url, '_blank');
  }
};

const formatVideoTime = (seconds: number): string => {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  if (h > 0) {
    return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  }
  return `${m}:${s.toString().padStart(2, '0')}`;
};

const formatDateTime = (dateStr: string): string => {
  return new Date(dateStr).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  });
};

onMounted(loadData);
</script>

<style scoped lang="scss">
.report-page {
  padding: 20px;
  background: #f5f7fa;
  min-height: calc(100vh - 60px);

  .page-header {
    margin-bottom: 20px;
    h2 {
      margin: 0;
      font-size: 20px;
      font-weight: 600;
      color: #303133;
    }
  }

  .table-card {
    background: #fff;
    border-radius: 8px;
    box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);

    :deep(.el-card__body) {
      padding: 20px;
    }
  }

  .report-tabs {
    margin-bottom: 20px;

    .tab-label {
      display: flex;
      align-items: center;
      gap: 6px;

      .tab-badge {
        margin-left: 4px;
      }
    }
  }

  .report-table {
    :deep(.el-table__header) {
      th {
        background: #fafafa;
        font-weight: 600;
        color: #606266;
      }
    }

    :deep(.el-table__row) {
      &:hover {
        background: #f5f7fa;
      }
    }
  }

  .content-cell {
    .content-header {
      display: flex;
      align-items: center;
      margin-bottom: 8px;
    }

    .target-info {
      margin-bottom: 8px;

      .target-title {
        display: flex;
        align-items: center;
        gap: 6px;
        font-weight: 500;
        margin-bottom: 6px;
        color: #303133;
        font-size: 14px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;

        .el-icon {
          color: var(--el-color-primary);
          flex-shrink: 0;
        }
      }

      .target-content {
        display: flex;
        align-items: flex-start;
        gap: 6px;
        margin-bottom: 6px;
        color: #606266;
        font-size: 13px;
        line-height: 1.5;

        .el-icon {
          color: var(--el-color-info);
          margin-top: 2px;
          flex-shrink: 0;
        }

        span {
          overflow: hidden;
          text-overflow: ellipsis;
          display: -webkit-box;
          -webkit-line-clamp: 2;
          -webkit-box-orient: vertical;
        }
      }

      .target-meta {
        display: flex;
        align-items: center;
        gap: 12px;
        flex-wrap: wrap;
        font-size: 12px;

        .meta-item {
          display: flex;
          align-items: center;
          gap: 4px;
          color: #909399;

          .el-icon {
            font-size: 14px;
          }
        }
      }
    }

    .target-missing {
      display: flex;
      align-items: center;
      gap: 6px;
      color: #909399;
      font-size: 12px;
      margin-bottom: 8px;

      .el-icon {
        color: var(--el-color-warning);
      }
    }

    .description-text {
      display: flex;
      align-items: flex-start;
      gap: 6px;
      color: #606266;
      font-size: 12px;
      margin-top: 8px;
      padding-top: 8px;
      border-top: 1px solid #f0f0f0;

      .el-icon {
        color: #909399;
        margin-top: 2px;
        flex-shrink: 0;
      }

      span {
        overflow: hidden;
        text-overflow: ellipsis;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
      }
    }
  }

  .reporter-cell {
    .reporter-info,
    .time-info {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 13px;
      color: #606266;
      margin-bottom: 6px;

      .el-icon {
        color: #909399;
        font-size: 14px;
      }
    }

    .time-info {
      font-size: 12px;
      color: #909399;
      margin-bottom: 0;
    }
  }

  .pagination-container {
    margin-top: 20px;
    display: flex;
    justify-content: flex-end;
    padding-top: 20px;
    border-top: 1px solid #ebeef5;
  }
}
</style>
