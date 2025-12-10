<template>
  <div class="upload-page">
    <div class="upload-container">
      <h1 class="page-title">上传视频</h1>

      <!-- 步骤指示器 -->
      <UploadSteps :active="currentStep" />

      <!-- 步骤 1: 选择文件 -->
      <div v-show="currentStep === 0" class="step-content">
        <FileSelector
          :video-file="videoFile"
          :cover-file="coverFile"
          :subtitle-file="subtitleFile"
          :video-preview-url="videoPreviewUrl"
          :cover-preview-url="coverPreviewUrl"
          @video-selected="handleVideoSelected"
          @cover-selected="handleCoverSelected"
          @subtitle-selected="handleSubtitleSelected"
          @video-removed="handleVideoRemoved"
          @cover-removed="handleCoverRemoved"
          @subtitle-removed="handleSubtitleRemoved"
        />

        <div class="step-actions">
          <el-button
            type="primary"
            size="large"
            :disabled="!hasVideoFile"
            @click="nextStep"
          >
            下一步
          </el-button>
        </div>
      </div>

      <!-- 步骤 2: 填写信息 -->
      <div v-show="currentStep === 1" class="step-content">
        <VideoInfoForm
          ref="videoFormRef"
          :categories="categories"
          :model-value="videoForm"
          @update:modelValue="handleVideoFormUpdate"
        />

        <div class="step-actions">
          <el-button size="large" @click="prevStep">上一步</el-button>
          <el-button
            type="primary"
            size="large"
            :loading="uploading"
            @click="handleStartUpload"
          >
            开始上传
          </el-button>
        </div>
      </div>

      <!-- 步骤 3: 上传进度 -->
      <div v-show="currentStep === 2" class="step-content">
        <UploadProgress
          :status="uploadStatus"
          :detail="uploadDetail"
          :progress="totalProgress"
          :complete="uploadComplete"
          :uploading="uploading"
          :uploaded-chunks="uploadedChunks"
          :total-chunks="totalChunks"
          :speed="uploadSpeed"
          :remaining-time="remainingTime"
          @resume="handleResumeUpload"
          @pause="handlePauseUpload"
          @go-home="goToHome"
          @upload-another="uploadAnother"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import UploadSteps from "@/components/upload/UploadSteps.vue";
import FileSelector from "@/components/upload/FileSelector.vue";
import VideoInfoForm from "@/components/upload/VideoInfoForm.vue";
import UploadProgress from "@/components/upload/UploadProgress.vue";
import { getCategories } from "@/api/category";
import { useFileUpload } from "@/composables/useFileUpload";
import { useChunkUpload } from "@/composables/useChunkUpload";
import type { Category } from "@/types/entity";

const router = useRouter();

// 步骤控制
const currentStep = ref<number>(0);

// 文件上传 composable
const {
  videoFile,
  coverFile,
  subtitleFile,
  videoPreviewUrl,
  coverPreviewUrl,
  selectVideoFile,
  selectCoverFile,
  selectSubtitleFile,
  removeVideoFile,
  removeCoverFile,
  removeSubtitleFile,
  resetFiles,
} = useFileUpload();

// 分片上传 composable
const {
  uploading,
  uploadComplete,
  uploadStatus,
  uploadDetail,
  totalChunks,
  uploadedChunks,
  totalProgress,
  uploadSpeed,
  remainingTime,
  startUpload,
  pauseUpload,
  resumeUpload,
  resetUpload,
} = useChunkUpload();

// 表单引用
const videoFormRef = ref<InstanceType<typeof VideoInfoForm> | null>(null);

// 表单数据
const videoForm = reactive<{
  title: string;
  description: string;
  category_id: number | null;
}>({
  title: "",
  description: "",
  category_id: null,
});

// 处理子组件表单更新（避免直接替换 reactive 对象）
const handleVideoFormUpdate = (value: {
  title: string;
  description: string;
  category_id: number | null;
}) => {
  videoForm.title = value.title ?? "";
  videoForm.description = value.description ?? "";
  videoForm.category_id =
    value.category_id === null || value.category_id === undefined
      ? null
      : value.category_id;
};

// 分类数据
const categories = ref<Category[]>([]);

// 计算属性
const hasVideoFile = computed(() => !!videoFile.value);

// 加载分类
const loadCategories = async () => {
  try {
    const res = await getCategories();
    if (Array.isArray(res)) {
      categories.value = res;
    } else if (res && res.data) {
      categories.value = res.data as Category[];
    } else {
      categories.value = [];
    }

    // 添加调试信息
    console.log("加载的分类列表:", categories.value);

    if (categories.value.length === 0) {
      console.warn("分类列表为空");
      ElMessage.warning("暂无可用分类，请联系管理员添加分类");
    }
  } catch (error) {
    console.error("加载分类失败:", error);
    ElMessage.error("加载分类失败，请稍后重试");
    categories.value = [];
  }
};

// 文件选择处理
const handleVideoSelected = (file: File) => {
  if (selectVideoFile(file)) {
    // 自动填充标题（去掉扩展名）
    if (!videoForm.title) {
      videoForm.title = file.name.replace(/\.[^/.]+$/, "");
    }
  }
};

const handleCoverSelected = (file: File) => {
  selectCoverFile(file);
};

const handleSubtitleSelected = (file: File) => {
  selectSubtitleFile(file);
};

// 文件移除处理
const handleVideoRemoved = () => {
  removeVideoFile();
};

const handleCoverRemoved = () => {
  removeCoverFile();
};

const handleSubtitleRemoved = () => {
  removeSubtitleFile();
};

// 步骤控制
const nextStep = () => {
  currentStep.value++;
};

const prevStep = () => {
  currentStep.value--;
};

// 开始上传
const handleStartUpload = async () => {
  if (!videoFile.value) {
    ElMessage.error("请先选择视频文件");
    return;
  }

  // 添加调试日志
  console.log("开始上传，当前表单数据:", videoForm);
  console.log(
    "category_id:",
    videoForm.category_id,
    "类型:",
    typeof videoForm.category_id
  );

  // 先验证表单
  let valid = false;
  try {
    if (
      !videoFormRef.value ||
      typeof videoFormRef.value.validate !== "function"
    ) {
      console.warn("videoFormRef 未挂载或无 validate 方法");
      valid = false;
    } else {
      valid = (await videoFormRef.value.validate()) ?? false;
    }
  } catch (err) {
    console.error("表单验证失败:", err);
    valid = false;
  }

  if (!valid) {
    ElMessage.error("请完善视频信息");
    return;
  }

  // 再次确认分类已选择
  if (!videoForm.category_id) {
    ElMessage.error("请选择视频分类");
    return;
  }

  currentStep.value = 2;

  try {
    await startUpload(
      videoFile.value,
      {
        title: videoForm.title,
        description: videoForm.description,
        category_id: videoForm.category_id,
      },
      coverFile.value,
      subtitleFile.value
    );
  } catch (error) {
    // 错误已在 composable 中处理
    console.error("上传失败:", error);
  }
};

// 暂停上传
const handlePauseUpload = () => {
  pauseUpload();
};

// 继续上传
const handleResumeUpload = async () => {
  if (!videoFile.value) {
    ElMessage.error("视频文件不存在");
    return;
  }

  if (!videoForm.category_id) {
    ElMessage.error("请选择视频分类");
    return;
  }

  try {
    await resumeUpload(
      videoFile.value,
      {
        title: videoForm.title,
        description: videoForm.description,
        category_id: videoForm.category_id,
      },
      coverFile.value,
      subtitleFile.value
    );
  } catch (error) {
    console.error("继续上传失败:", error);
  }
};

// 返回首页
const goToHome = () => {
  router.push("/");
};

// 继续上传（重置状态）
const uploadAnother = () => {
  // 重置所有状态
  currentStep.value = 0;
  resetFiles();
  resetUpload();
  videoForm.title = "";
  videoForm.description = "";
  videoForm.category_id = null;
};

// 初始化
onMounted(async () => {
  await loadCategories();
});
</script>

<style lang="scss" scoped>
.upload-page {
  min-height: 100vh;
  background: var(--bg-light);
  padding: var(--spacing-xl) 0;
}

.upload-container {
  max-width: 900px;
  margin: 0 auto;
  padding: 0 var(--spacing-lg);
}

.page-title {
  font-size: var(--font-size-2xl);
  font-weight: 600;
  text-align: center;
  margin-bottom: var(--spacing-xl);
  color: var(--text-primary);
}

.step-content {
  margin-top: var(--spacing-2xl);
  background: var(--bg-white);
  border-radius: var(--radius-lg);
  padding: var(--spacing-2xl);
  box-shadow: var(--shadow-sm);
}

.step-actions {
  display: flex;
  justify-content: center;
  gap: var(--spacing-md);
  margin-top: var(--spacing-2xl);
}

@media (max-width: 768px) {
  .upload-container {
    padding: 0 var(--spacing-md);
  }

  .step-content {
    padding: var(--spacing-lg);
  }
}
</style>
