<template>
  <el-dialog
    v-model="visible"
    title="选择收藏文件夹"
    width="500px"
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <div class="folder-dialog-content">
      <!-- 创建新文件夹 -->
      <div class="create-folder-section">
        <el-button 
          type="primary" 
          :icon="Plus" 
          @click="showCreateForm = true"
          class="create-btn"
        >
          新建文件夹
        </el-button>
        
        <div v-if="showCreateForm" class="create-form">
          <el-input
            v-model="newFolderName"
            placeholder="文件夹名称"
            class="folder-name-input"
            @keyup.enter="handleCreateFolder"
          />
          <div class="form-actions">
            <el-button size="small" @click="cancelCreate">取消</el-button>
            <el-button type="primary" size="small" @click="handleCreateFolder">创建</el-button>
          </div>
        </div>
      </div>

      <!-- 文件夹列表 -->
      <div class="folders-list">
        <div 
          v-for="folder in folders" 
          :key="folder.id"
          class="folder-item"
          :class="{ active: selectedFolderId === folder.id }"
          @click="selectFolder(folder.id)"
        >
          <el-icon class="folder-icon"><Folder /></el-icon>
          <span class="folder-name">{{ folder.name }}</span>
          <span class="folder-count">({{ folder.count }})</span>
        </div>
        
        <!-- 未分类选项 -->
        <div 
          class="folder-item"
          :class="{ active: selectedFolderId === null }"
          @click="selectFolder(null)"
        >
          <el-icon class="folder-icon"><Document /></el-icon>
          <span class="folder-name">未分类</span>
          <span class="folder-count">({{ uncategorizedCount }})</span>
        </div>
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="handleClose">取消</el-button>
        <el-button type="primary" @click="handleConfirm" :disabled="selectedFolderId === undefined">
          确定
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import { ElMessage } from 'element-plus';
import { Plus, Folder, Document } from '@element-plus/icons-vue';
import { request } from '@/shared/utils/request';
import type { ApiResponse } from '@/shared/types/entity';

interface Folder {
  id: number;
  name: string;
  description?: string;
  count: number;
  created_at: string;
}

const props = defineProps<{
  modelValue: boolean;
}>();

const emit = defineEmits<{
  'update:modelValue': [value: boolean];
  'confirm': [folderId: number | null];
}>();

const visible = ref(false);
const folders = ref<Folder[]>([]);
const uncategorizedCount = ref(0);
const selectedFolderId = ref<number | null | undefined>(undefined);
const showCreateForm = ref(false);
const newFolderName = ref('');

watch(() => props.modelValue, (val) => {
  visible.value = val;
  if (val) {
    loadFolders();
    selectedFolderId.value = undefined;
    showCreateForm.value = false;
    newFolderName.value = '';
  }
});

watch(visible, (val) => {
  emit('update:modelValue', val);
});

const loadFolders = async () => {
  try {
    const res = await request.get<ApiResponse<{ folders: Folder[]; uncategorized_count: number }>>('/users/me/favorites/folders');
    if (res.success && res.data) {
      folders.value = res.data.folders;
      uncategorizedCount.value = res.data.uncategorized_count;
    }
  } catch (error) {
    console.error('加载文件夹列表失败:', error);
    ElMessage.error('加载文件夹列表失败');
  }
};

const selectFolder = (folderId: number | null) => {
  selectedFolderId.value = folderId;
};

const handleCreateFolder = async () => {
  if (!newFolderName.value.trim()) {
    ElMessage.warning('请输入文件夹名称');
    return;
  }

  try {
    const res = await request.post<ApiResponse<Folder>>('/users/me/favorites/folders', {
      name: newFolderName.value.trim()
    });
    if (res.success && res.data) {
      ElMessage.success('创建成功');
      await loadFolders();
      selectedFolderId.value = res.data.id;
      showCreateForm.value = false;
      newFolderName.value = '';
    }
  } catch (error: any) {
    console.error('创建文件夹失败:', error);
    ElMessage.error(error.response?.data?.detail || '创建文件夹失败');
  }
};

const cancelCreate = () => {
  showCreateForm.value = false;
  newFolderName.value = '';
};

const handleConfirm = () => {
  if (selectedFolderId.value === undefined) {
    ElMessage.warning('请选择文件夹');
    return;
  }
  emit('confirm', selectedFolderId.value);
  handleClose();
};

const handleClose = () => {
  visible.value = false;
  selectedFolderId.value = undefined;
  showCreateForm.value = false;
  newFolderName.value = '';
};
</script>

<style scoped lang="scss">
.folder-dialog-content {
  padding: 20px 0;
}

.create-folder-section {
  margin-bottom: 20px;
  padding-bottom: 20px;
  border-bottom: 1px solid var(--border-light);

  .create-btn {
    width: 100%;
  }

  .create-form {
    margin-top: 12px;
    padding: 12px;
    background: var(--bg-gray-1);
    border-radius: var(--radius-md);

    .folder-name-input {
      margin-bottom: 12px;
    }

    .form-actions {
      display: flex;
      justify-content: flex-end;
      gap: 8px;
    }
  }
}

.folders-list {
  max-height: 400px;
  overflow-y: auto;

  .folder-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px;
    border-radius: var(--radius-md);
    cursor: pointer;
    transition: all 0.2s;

    &:hover {
      background: var(--bg-gray-1);
    }

    &.active {
      background: var(--primary-light);
      color: var(--primary-color);

      .folder-icon {
        color: var(--primary-color);
      }
    }

    .folder-icon {
      font-size: 20px;
    }

    .folder-name {
      flex: 1;
      font-size: 14px;
    }

    .folder-count {
      font-size: 12px;
      color: var(--text-tertiary);
    }
  }
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
</style>

