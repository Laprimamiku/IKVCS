<template>
  <div class="report-page">
    <div class="tabs">
      <div
        v-for="status in [0, 1, 2]"
        :key="status"
        class="tab-item"
        :class="{ active: currentStatus === status }"
        @click="switchTab(status)"
      >
        {{ statusMap[status] }}
      </div>
    </div>

    <div class="table-container">
      <table class="data-table">
        <thead>
          <tr>
            <th>类型</th>
            <th>被举报对象ID</th>
            <th>举报原因</th>
            <th>描述</th>
            <th>举报人</th>
            <th>时间</th>
            <th v-if="currentStatus === 0">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in reports" :key="item.id">
            <td>
              <span class="tag" :class="item.target_type">{{
                item.target_type
              }}</span>
            </td>
            <td>{{ item.target_id }}</td>
            <td>{{ item.reason }}</td>
            <td class="desc-cell" :title="item.description">
              {{ item.description || "-" }}
            </td>
            <td>{{ item.reporter.nickname }}</td>
            <td>{{ new Date(item.created_at).toLocaleString() }}</td>
            <td v-if="currentStatus === 0" class="actions-cell">
              <button
                class="btn link-danger"
                @click="handleReport(item.id, 'delete_target')"
              >
                删除违规内容
              </button>
              <button
                class="btn link-info"
                @click="handleReport(item.id, 'ignore')"
              >
                忽略
              </button>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="reports.length === 0" class="no-data">暂无数据</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { adminApi, type ReportItem } from "../api/admin.api";

const currentStatus = ref(0);
const reports = ref<ReportItem[]>([]);
const statusMap: Record<number, string> = {
  0: "待处理",
  1: "已处理",
  2: "已忽略",
};

const loadData = async () => {
  try {
    const res = await adminApi.getReports(currentStatus.value);
    // 修复：正确解析API响应数据
    // 后端直接返回字典格式，request拦截器会包装成 { success: true, data: {...} }
    if (res.success && res.data) {
      // 后端返回格式：{ items: [...], total: ..., page: ..., page_size: ..., total_pages: ... }
      if (res.data.items && Array.isArray(res.data.items)) {
        reports.value = res.data.items;
      } else if (Array.isArray(res.data)) {
        reports.value = res.data;
      } else {
        reports.value = [];
      }
    } else {
      reports.value = [];
    }
  } catch (e) {
    console.error('加载举报列表失败:', e);
    reports.value = [];
  }
};

const switchTab = (status: number) => {
  currentStatus.value = status;
  loadData();
};

const handleReport = async (id: number, action: "delete_target" | "ignore") => {
  const confirmText =
    action === "delete_target"
      ? "确认删除该违规内容吗？此操作不可逆（软删除）"
      : "确认忽略该举报吗？";
  if (!confirm(confirmText)) return;

  try {
    await adminApi.handleReport(id, action);
    loadData(); // 刷新列表
  } catch (e) {
    alert("操作失败");
  }
};

onMounted(loadData);
</script>

<style scoped lang="scss">
.report-page {
  background: #fff;
  border-radius: 8px;
  min-height: 600px;
  padding: 20px;

  .tabs {
    display: flex;
    border-bottom: 1px solid #e7e7e7;
    margin-bottom: 20px;

    .tab-item {
      padding: 10px 24px;
      cursor: pointer;
      color: #666;
      border-bottom: 2px solid transparent;
      &:hover {
        color: var(--primary-color);
      }
      &.active {
        color: var(--primary-color);
        border-bottom-color: var(--primary-color);
      }
    }
  }

  .data-table {
    width: 100%;
    border-collapse: collapse;

    th,
    td {
      text-align: left;
      padding: 12px 16px;
      border-bottom: 1px solid #f0f0f0;
      font-size: 14px;
    }

    th {
      background: #fafafa;
      color: #999;
      font-weight: normal;
    }

    .desc-cell {
      max-width: 200px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .tag {
      font-size: 12px;
      padding: 2px 6px;
      border-radius: 4px;
      &.VIDEO {
        background: #e7f6ff;
        color: #00aeec;
      }
      &.COMMENT {
        background: #ebf9e5;
        color: #67c23a;
      }
      &.DANMAKU {
        background: #fef0f0;
        color: #f56c6c;
      }
    }

    .actions-cell {
      .btn {
        background: none;
        border: none;
        cursor: pointer;
        padding: 0 8px;
        font-size: 13px;
        &.link-danger {
          color: #f56c6c;
        }
        &.link-info {
          color: #909399;
        }
        &:hover {
          text-decoration: underline;
        }
      }
    }
  }

  .no-data {
    text-align: center;
    padding: 40px;
    color: #999;
  }
}
</style>
