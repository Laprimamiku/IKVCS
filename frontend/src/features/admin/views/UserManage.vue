<template>
  <div class="user-manage-page">
    <div class="filter-bar">
      <div class="search-box">
        <i class="iconfont icon-search"></i>
        <input
          v-model="searchKeyword"
          type="text"
          placeholder="搜索用户名 / 昵称"
          @keyup.enter="handleSearch"
        />
        <button class="search-btn" @click="handleSearch">搜索</button>
      </div>
    </div>

    <div class="table-container">
      <table class="data-table">
        <thead>
          <tr>
            <th width="80">ID</th>
            <th width="250">用户信息</th>
            <th width="100">角色</th>
            <th width="100">状态</th>
            <th>注册时间</th>
            <th>最后登录</th>
            <th width="150" class="text-right">操作</th>
          </tr>
        </thead>
        <tbody v-if="!loading && users.length > 0">
          <tr v-for="user in users" :key="user.id">
            <td>{{ user.id }}</td>
            <td>
              <div class="user-cell">
                <img
                  :src="user.avatar || defaultAvatar"
                  class="avatar"
                  alt="avatar"
                  @error="handleImgError"
                />
                <div class="info">
                  <div class="nickname">{{ user.nickname }}</div>
                  <div class="username">@{{ user.username }}</div>
                </div>
              </div>
            </td>
            <td>
              <span class="role-tag" :class="{ admin: user.role === 'admin' }">
                {{ user.role === "admin" ? "管理员" : "用户" }}
              </span>
            </td>
            <td>
              <span
                class="status-dot"
                :class="user.status === 1 ? 'active' : 'banned'"
              ></span>
              {{ user.status === 1 ? "正常" : "已封禁" }}
            </td>
            <td class="time-cell">{{ formatDate(user.created_at) }}</td>
            <td class="time-cell">
              {{
                user.last_login_time ? formatDate(user.last_login_time) : "-"
              }}
            </td>
            <td class="text-right actions-cell">
              <template v-if="user.role !== 'admin'">
                <button
                  v-if="user.status === 1"
                  class="btn link-danger"
                  @click="handleBan(user)"
                >
                  封禁
                </button>
                <button
                  v-else
                  class="btn link-success"
                  @click="handleUnban(user)"
                >
                  解封
                </button>
              </template>
              <span v-else class="disabled-text">不可操作</span>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="loading" class="loading-state">
        <div class="spinner"></div>
        加载中...
      </div>

      <div v-if="!loading && users.length === 0" class="empty-state">
        暂无用户数据
      </div>
    </div>

    <div class="pagination" v-if="total > pageSize">
      <button
        :disabled="currentPage === 1"
        @click="changePage(currentPage - 1)"
      >
        上一页
      </button>
      <span class="page-info">{{ currentPage }} / {{ totalPages }}</span>
      <button
        :disabled="currentPage === totalPages"
        @click="changePage(currentPage + 1)"
      >
        下一页
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import { adminApi } from "../api/admin.api";
import type { UserInfo } from "@/shared/types/entity"; // 确保 entity.ts 中有 UserInfo 定义
import defaultAvatarImg from "@/shared/assets/vue.svg"; // 这里的默认头像路径请根据实际情况调整

// 扩展 UserInfo 接口以包含 status 字段 (如果 entity.ts 中未定义)
interface AdminUserItem extends UserInfo {
  status: number; // 0=封禁, 1=正常
}

const loading = ref(false);
const users = ref<AdminUserItem[]>([]);
const total = ref(0);
const currentPage = ref(1);
const pageSize = 20;
const searchKeyword = ref("");
const defaultAvatar = defaultAvatarImg;

const totalPages = computed(() => Math.ceil(total.value / pageSize));

// 格式化时间
const formatDate = (dateStr: string) => {
  return new Date(dateStr).toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
};

// 头像加载失败处理
const handleImgError = (e: Event) => {
  const target = e.target as HTMLImageElement;
  target.src = defaultAvatar;
};

// 加载数据
const fetchData = async () => {
  loading.value = true;
  try {
    const res = await adminApi.getUsers(currentPage.value, searchKeyword.value);
    // 修复：正确解析API响应数据
    // 后端直接返回字典格式，request拦截器会包装成 { success: true, data: {...} }
    if (res.success && res.data) {
      // 后端返回格式：{ items: [...], total: ..., page: ..., page_size: ..., total_pages: ... }
      if (res.data.items && Array.isArray(res.data.items)) {
        users.value = res.data.items;
        total.value = res.data.total || 0;
      } else if (Array.isArray(res.data)) {
        users.value = res.data;
        total.value = res.data.length;
      } else {
        users.value = [];
        total.value = 0;
      }
    } else {
      users.value = [];
      total.value = 0;
    }
  } catch (error) {
    console.error("获取用户列表失败", error);
    users.value = [];
    total.value = 0;
  } finally {
    loading.value = false;
  }
};

// 搜索
const handleSearch = () => {
  currentPage.value = 1;
  fetchData();
};

// 翻页
const changePage = (page: number) => {
  if (page < 1 || page > totalPages.value) return;
  currentPage.value = page;
  fetchData();
};

// 封禁用户
const handleBan = async (user: AdminUserItem) => {
  if (!confirm(`确定要封禁用户 "${user.nickname}" 吗？该用户将无法登录。`))
    return;

  try {
    await adminApi.banUser(user.id);
    user.status = 0; // 乐观更新UI
    // alert('用户已封禁'); // 可选：使用全局 Toast 替代
  } catch (e) {
    alert("操作失败");
  }
};

// 解封用户
const handleUnban = async (user: AdminUserItem) => {
  if (!confirm(`确定要解封用户 "${user.nickname}" 吗？`)) return;

  try {
    await adminApi.unbanUser(user.id);
    user.status = 1; // 乐观更新UI
  } catch (e) {
    alert("操作失败");
  }
};

onMounted(() => {
  fetchData();
});
</script>

<style scoped lang="scss">
.user-manage-page {
  background: #fff;
  border-radius: 8px;
  min-height: 600px;
  padding: 24px;
  display: flex;
  flex-direction: column;

  /* 顶部搜索栏 */
  .filter-bar {
    margin-bottom: 24px;
    display: flex;
    justify-content: flex-end;

    .search-box {
      display: flex;
      align-items: center;
      border: 1px solid #e7e7e7;
      border-radius: 4px;
      padding: 0 4px 0 12px;
      width: 300px;
      transition: border-color 0.2s;

      &:focus-within {
        border-color: var(--primary-color);
      }

      .iconfont {
        color: #999;
        margin-right: 8px;
      }

      input {
        border: none;
        outline: none;
        height: 36px;
        flex: 1;
        font-size: 14px;
        color: #18191c;
      }

      .search-btn {
        background: var(--primary-color);
        color: #fff;
        border: none;
        height: 28px;
        padding: 0 12px;
        border-radius: 4px;
        margin-left: 8px;
        cursor: pointer;
        font-size: 13px;
        transition: opacity 0.2s;

        &:hover {
          opacity: 0.9;
        }
      }
    }
  }

  /* 表格区域 */
  .table-container {
    flex: 1;
    overflow-x: auto;
  }

  .data-table {
    width: 100%;
    border-collapse: collapse;
    table-layout: fixed;

    th,
    td {
      padding: 14px 16px;
      text-align: left;
      border-bottom: 1px solid #f0f0f0;
      font-size: 14px;
      color: #18191c;
    }

    th {
      background: #fafafa;
      color: #999;
      font-weight: normal;
    }

    tr:hover {
      background-color: #f4f5f7;
    }

    /* 用户单元格 */
    .user-cell {
      display: flex;
      align-items: center;

      .avatar {
        width: 36px;
        height: 36px;
        border-radius: 50%;
        margin-right: 12px;
        object-fit: cover;
        border: 1px solid #f0f0f0;
        background-color: #eee;
      }

      .info {
        display: flex;
        flex-direction: column;
        justify-content: center;
        overflow: hidden;

        .nickname {
          font-weight: 500;
          line-height: 1.2;
          margin-bottom: 2px;
        }

        .username {
          font-size: 12px;
          color: #999;
        }
      }
    }

    /* 角色标签 */
    .role-tag {
      display: inline-block;
      padding: 2px 8px;
      border-radius: 4px;
      font-size: 12px;
      background: #f4f5f7;
      color: #61666d;

      &.admin {
        background: #fff1e6;
        color: #ffb027;
        border: 1px solid rgba(255, 176, 39, 0.3);
      }
    }

    /* 状态指示点 */
    .status-dot {
      display: inline-block;
      width: 6px;
      height: 6px;
      border-radius: 50%;
      margin-right: 6px;
      background: #ccc;

      &.active {
        background: #67c23a;
      }
      &.banned {
        background: #f56c6c;
      }
    }

    .time-cell {
      color: #999;
      font-size: 13px;
    }

    .text-right {
      text-align: right;
    }

    /* 操作按钮 */
    .actions-cell {
      .btn {
        background: none;
        border: none;
        cursor: pointer;
        padding: 4px 8px;
        font-size: 13px;
        border-radius: 4px;
        transition: background-color 0.2s;

        &.link-danger {
          color: #f56c6c;
          &:hover {
            background: rgba(245, 108, 108, 0.1);
          }
        }

        &.link-success {
          color: #67c23a;
          &:hover {
            background: rgba(103, 194, 58, 0.1);
          }
        }
      }

      .disabled-text {
        color: #ccc;
        font-size: 12px;
        padding-right: 8px;
      }
    }
  }

  .loading-state,
  .empty-state {
    padding: 60px 0;
    text-align: center;
    color: #999;
    font-size: 14px;
  }

  .spinner {
    display: inline-block;
    width: 20px;
    height: 20px;
    border: 2px solid #e7e7e7;
    border-top-color: var(--primary-color);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
    vertical-align: middle;
    margin-right: 8px;
  }

  /* 分页 */
  .pagination {
    margin-top: 20px;
    display: flex;
    justify-content: flex-end;
    align-items: center;
    gap: 12px;

    button {
      padding: 6px 12px;
      background: #fff;
      border: 1px solid #dcdfe6;
      border-radius: 4px;
      cursor: pointer;
      font-size: 13px;
      color: #606266;

      &:hover:not(:disabled) {
        border-color: var(--primary-color);
        color: var(--primary-color);
      }

      &:disabled {
        background: #f5f7fa;
        color: #c0c4cc;
        cursor: not-allowed;
      }
    }

    .page-info {
      font-size: 13px;
      color: #606266;
    }
  }
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
