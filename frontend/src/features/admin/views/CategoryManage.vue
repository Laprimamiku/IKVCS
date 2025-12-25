<template>
  <div class="category-manage-page">
    <div class="page-header">
      <h2>分类管理</h2>
      <el-button class="add-btn" type="primary" @click="showAddDialog = true">
        <i class="iconfont icon-plus"></i> 新增分类
      </el-button>
    </div>

    <div class="table-container">
      <table class="data-table">
        <thead>
          <tr>
            <th width="80">ID</th>
            <th>分类名称</th>
            <th>描述</th>
            <th>视频数量</th>
            <th width="200" class="text-right">操作</th>
          </tr>
        </thead>
        <tbody v-if="!loading && categories.length > 0">
          <tr v-for="category in categories" :key="category.id">
            <td>{{ category.id }}</td>
            <td class="name-cell">{{ category.name }}</td>
            <td class="desc-cell" :title="category.description">
              {{ category.description || "-" }}
            </td>
            <td>{{ category.video_count || 0 }}</td>
            <td class="text-right actions-cell">
              <el-button class="btn link-primary" type="text" @click="handleEdit(category)">
                编辑
              </el-button>
              <button
                class="btn link-danger"
                @click="handleDelete(category)"
              >
                删除
              </button>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="loading" class="loading-state">
        <div class="spinner"></div>
        加载中...
      </div>

      <div v-if="!loading && categories.length === 0" class="empty-state">
        <div class="empty-icon">📂</div>
        <p>暂无分类数据</p>
      </div>
    </div>

    <!-- 新增/编辑对话框 -->
    <el-dialog
      v-model="showAddDialog"
      :title="editingCategory ? '编辑分类' : '新增分类'"
      width="500px"
    >
      <el-form :model="formData" label-width="80px">
        <el-form-item label="分类名称" required>
          <el-input
            v-model="formData.name"
            placeholder="请输入分类名称"
            maxlength="50"
            show-word-limit
          />
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="formData.description"
            type="textarea"
            :rows="3"
            placeholder="请输入分类描述（可选）"
            maxlength="200"
            show-word-limit
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { adminApi } from "../api/admin.api";
import type { Category } from "@/shared/types/entity";

interface CategoryWithCount extends Category {
  video_count?: number;
}

const loading = ref(false);
const categories = ref<CategoryWithCount[]>([]);
const showAddDialog = ref(false);
const editingCategory = ref<CategoryWithCount | null>(null);

const formData = ref({
  name: "",
  description: "",
});

// 加载数据
const loadData = async () => {
  loading.value = true;
  try {
    // 获取分类列表
    const res = await adminApi.getCategories();
    
    if (res.success && res.data) {
      const categoryList = Array.isArray(res.data) ? res.data : res.data.items || [];
      
      // 获取分类统计（包含视频数量）
      const statsRes = await adminApi.getCategoryStats();
      if (statsRes.success && statsRes.data) {
        const stats = Array.isArray(statsRes.data) ? statsRes.data : statsRes.data.items || [];
        const statsMap = new Map(stats.map((s: any) => [s.name, s.count]));
        
        categories.value = categoryList.map((cat: Category) => ({
          ...cat,
          video_count: statsMap.get(cat.name) || 0,
        }));
      } else {
        categories.value = categoryList;
      }
    } else {
      categories.value = [];
    }
  } catch (error) {
    console.error("加载分类列表失败", error);
    ElMessage.error("加载分类列表失败");
    categories.value = [];
  } finally {
    loading.value = false;
  }
};

// 编辑
const handleEdit = (category: CategoryWithCount) => {
  editingCategory.value = category;
  formData.value = {
    name: category.name,
    description: category.description || "",
  };
  showAddDialog.value = true;
};

// 删除
const handleDelete = async (category: CategoryWithCount) => {
  if (!category.id) return;
  
  try {
    await ElMessageBox.confirm(
      `确定要删除分类 "${category.name}" 吗？此操作不可逆。`,
      "确认删除",
      {
        confirmButtonText: "确定",
        cancelButtonText: "取消",
        type: "warning",
      }
    );

    await adminApi.deleteCategory(category.id);
    ElMessage.success("删除成功");
    loadData();
  } catch (error: any) {
    if (error !== "cancel") {
      console.error("删除分类失败", error);
      ElMessage.error(error?.response?.data?.detail || "删除失败");
    }
  }
};

// 提交表单
const handleSubmit = async () => {
  if (!formData.value.name.trim()) {
    ElMessage.warning("请输入分类名称");
    return;
  }

  try {
    if (editingCategory.value) {
      // 编辑
      await adminApi.updateCategory(editingCategory.value.id, formData.value);
      ElMessage.success("更新成功");
    } else {
      // 新增
      await adminApi.createCategory(formData.value);
      ElMessage.success("创建成功");
    }
    
    showAddDialog.value = false;
    editingCategory.value = null;
    formData.value = { name: "", description: "" };
    loadData();
  } catch (error: any) {
    console.error("操作失败", error);
    ElMessage.error(error?.response?.data?.detail || "操作失败");
  }
};

// 监听对话框关闭，重置表单
const resetForm = () => {
  editingCategory.value = null;
  formData.value = { name: "", description: "" };
};

onMounted(() => {
  loadData();
});
</script>

<style scoped lang="scss">
.category-manage-page {
  background: #fff;
  border-radius: 8px;
  min-height: 600px;
  padding: 24px;

  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;

    h2 {
      font-size: 20px;
      font-weight: 500;
      margin: 0;
    }

    .add-btn {
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 8px 16px;
      background: var(--primary-color);
      color: #fff;
      border: none;
      border-radius: 4px;
      cursor: pointer;
      font-size: 14px;
      transition: opacity 0.2s;

      &:hover {
        opacity: 0.9;
      }
    }
  }

  .table-container {
    .data-table {
      width: 100%;
      border-collapse: collapse;

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

      .name-cell {
        font-weight: 500;
      }

      .desc-cell {
        max-width: 300px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        color: #999;
      }

      .text-right {
        text-align: right;
      }

      .actions-cell {
        .btn {
          background: none;
          border: none;
          cursor: pointer;
          padding: 4px 8px;
          font-size: 13px;
          border-radius: 4px;
          margin-left: 8px;
          transition: background-color 0.2s;

          &.link-primary {
            color: #00aeec;
            &:hover {
              background: rgba(0, 174, 236, 0.1);
            }
          }

          &.link-danger {
            color: #f56c6c;
            &:hover {
              background: rgba(245, 108, 108, 0.1);
            }
          }
        }
      }
    }

    .loading-state,
    .empty-state {
      padding: 60px 0;
      text-align: center;
      color: #999;
      font-size: 14px;

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

      .empty-icon {
        font-size: 64px;
        margin-bottom: 16px;
        opacity: 0.5;
      }
    }
  }
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
