<template>
  <div class="upload-page">
    <div class="upload-container">
      <h1 class="page-title">上传视频</h1>

      <!-- 步骤指示器 -->
      <el-steps :active="currentStep" align-center finish-status="success">
        <el-step title="选择文件" />
        <el-step title="填写信息" />
        <el-step title="上传完成" />
      </el-steps>

      <!-- 步骤 1: 选择文件 -->
      <div v-show="currentStep === 0" class="step-content">
        <div class="upload-area">
          <!-- 视频上传区 -->
          <div class="file-upload-box" @click="triggerVideoSelect">
            <input
              ref="videoInput"
              type="file"
              accept="video/*"
              style="display: none"
              @change="handleVideoSelect"
            />
            <div v-if="!videoFile" class="upload-placeholder">
              <el-icon :size="60" color="#409EFF"><Upload /></el-icon>
              <p class="upload-text">点击选择视频文件</p>
              <p class="upload-hint">支持 MP4、AVI、MOV 等格式，最大 2GB</p>
            </div>
            <div v-else class="file-preview">
              <video
                v-if="videoPreviewUrl"
                :src="videoPreviewUrl"
                controls
                class="video-preview"
              />
              <div class="file-info">
                <p class="file-name">{{ videoFile.name }}</p>
                <p class="file-size">{{ formatFileSize(videoFile.size) }}</p>
                <el-button type="danger" size="small" @click.stop="removeVideo">
                  重新选择
                </el-button>
              </div>
            </div>
          </div>

          <!-- 封面上传区 -->
          <div class="cover-upload-section">
            <h3>视频封面</h3>
            <div class="cover-upload-box" @click="triggerCoverSelect">
              <input
                ref="coverInput"
                type="file"
                accept="image/*"
                style="display: none"
                @change="handleCoverSelect"
              />
              <div v-if="!coverFile" class="upload-placeholder small">
                <el-icon :size="40" color="#409EFF"><Picture /></el-icon>
                <p class="upload-text">选择封面图片</p>
              </div>
              <div v-else class="cover-preview">
                <img :src="coverPreviewUrl" alt="封面预览" />
                <el-button
                  type="danger"
                  size="small"
                  circle
                  class="remove-btn"
                  @click.stop="removeCover"
                >
                  <el-icon><Close /></el-icon>
                </el-button>
              </div>
            </div>
          </div>

          <!-- 字幕上传区 -->
          <div class="subtitle-upload-section">
            <h3>字幕文件（可选）</h3>
            <el-upload
              ref="subtitleUpload"
              :auto-upload="false"
              :limit="1"
              accept=".srt,.vtt,.json,.ass"
              :on-change="handleSubtitleSelect"
              :on-remove="handleSubtitleRemove"
            >
              <el-button type="primary" plain>
                <el-icon><Document /></el-icon>
                选择字幕文件
              </el-button>
              <template #tip>
                <div class="el-upload__tip">支持 SRT、VTT 格式</div>
              </template>
            </el-upload>
          </div>
        </div>

        <div class="step-actions">
          <el-button
            type="primary"
            size="large"
            :disabled="!videoFile"
            @click="nextStep"
          >
            下一步
          </el-button>
        </div>
      </div>

      <!-- 步骤 2: 填写信息 -->
      <div v-show="currentStep === 1" class="step-content">
        <el-form
          ref="videoFormRef"
          :model="videoForm"
          :rules="videoFormRules"
          label-width="100px"
          class="video-form"
        >
          <el-form-item label="视频标题" prop="title">
            <el-input
              v-model="videoForm.title"
              placeholder="请输入视频标题"
              maxlength="100"
              show-word-limit
            />
          </el-form-item>

          <el-form-item label="视频描述" prop="description">
            <el-input
              v-model="videoForm.description"
              type="textarea"
              :rows="5"
              placeholder="请输入视频描述"
              maxlength="500"
              show-word-limit
            />
          </el-form-item>

          <el-form-item label="视频分类" prop="category_id">
            <el-select
              v-model="videoForm.category_id"
              placeholder="请选择分类"
              style="width: 100%"
            >
              <el-option
                v-for="cat in categories"
                :key="cat.id"
                :label="cat.name"
                :value="cat.id"
              />
            </el-select>
          </el-form-item>
        </el-form>

        <div class="step-actions">
          <el-button size="large" @click="prevStep">上一步</el-button>
          <el-button
            type="primary"
            size="large"
            :loading="uploading"
            @click="startUpload"
          >
            开始上传
          </el-button>
        </div>
      </div>

      <!-- 步骤 3: 上传进度 -->
      <div v-show="currentStep === 2" class="step-content">
        <div class="upload-progress-section">
          <div class="progress-info">
            <h3>{{ uploadStatus }}</h3>
            <p class="progress-detail">{{ uploadDetail }}</p>
          </div>

          <!-- 总体进度 -->
          <div class="progress-bar-wrapper">
            <el-progress
              :percentage="totalProgress"
              :status="uploadComplete ? 'success' : undefined"
              :stroke-width="20"
            />
          </div>

          <!-- 详细进度信息 -->
          <div class="progress-details">
            <div class="detail-item">
              <span class="label">已上传分片：</span>
              <span class="value"
                >{{ uploadedChunks }} / {{ totalChunks }}</span
              >
            </div>
            <div class="detail-item">
              <span class="label">上传速度：</span>
              <span class="value">{{ uploadSpeed }}</span>
            </div>
            <div class="detail-item">
              <span class="label">剩余时间：</span>
              <span class="value">{{ remainingTime }}</span>
            </div>
          </div>

          <!-- 操作按钮 -->
          <div class="step-actions">
            <el-button
              v-if="!uploadComplete && !uploading"
              type="primary"
              size="large"
              @click="resumeUpload"
            >
              继续上传
            </el-button>
            <el-button
              v-if="uploading"
              type="warning"
              size="large"
              @click="pauseUpload"
            >
              暂停上传
            </el-button>
            <el-button
              v-if="uploadComplete"
              type="success"
              size="large"
              @click="goToHome"
            >
              返回首页
            </el-button>
            <el-button
              v-if="uploadComplete"
              size="large"
              @click="uploadAnother"
            >
              继续上传
            </el-button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { Upload, Picture, Document, Close } from "@element-plus/icons-vue";
import { getCategories } from "@/api/category";
import {
  initUpload,
  uploadChunk,
  finishUpload,
  getUploadProgress,
} from "@/api/upload";
import { uploadVideoCover, uploadVideoSubtitle } from "@/api/video";

const router = useRouter();

// 步骤控制
const currentStep = ref(0);

// 文件相关
const videoInput = ref(null);
const coverInput = ref(null);
const subtitleUpload = ref(null);
const videoFile = ref(null);
const coverFile = ref(null);
const subtitleFile = ref(null);
const videoPreviewUrl = ref("");
const coverPreviewUrl = ref("");

// 表单相关
const videoFormRef = ref(null);
const videoForm = reactive({
  title: "",
  description: "",
  category_id: null,
});

const videoFormRules = {
  title: [
    { required: true, message: "请输入视频标题", trigger: "blur" },
    {
      min: 1,
      max: 100,
      message: "标题长度在 1 到 100 个字符",
      trigger: "blur",
    },
  ],
  description: [
    { max: 500, message: "描述长度不能超过 500 个字符", trigger: "blur" },
  ],
  category_id: [
    { required: true, message: "请选择视频分类", trigger: "change" },
  ],
};

// 分类数据
const categories = ref([]);

// 上传相关
const uploading = ref(false);
const uploadComplete = ref(false);
const uploadStatus = ref("准备上传...");
const uploadDetail = ref("");
const fileHash = ref("");
const totalChunks = ref(0);
const uploadedChunks = ref(0);
const chunkSize = 5 * 1024 * 1024; // 5MB
const uploadStartTime = ref(0);
const uploadedBytes = ref(0);

// 计算属性
const totalProgress = computed(() => {
  if (totalChunks.value === 0) return 0;
  return Math.floor((uploadedChunks.value / totalChunks.value) * 100);
});

const uploadSpeed = computed(() => {
  if (uploadStartTime.value === 0) return "0 KB/s";
  const elapsed = (Date.now() - uploadStartTime.value) / 1000; // 秒
  if (elapsed === 0) return "0 KB/s";
  const speed = uploadedBytes.value / elapsed;
  return formatSpeed(speed);
});

const remainingTime = computed(() => {
  if (uploadStartTime.value === 0 || uploadedBytes.value === 0)
    return "计算中...";
  const elapsed = (Date.now() - uploadStartTime.value) / 1000;
  const speed = uploadedBytes.value / elapsed;
  if (speed === 0) return "计算中...";
  const remaining = (videoFile.value.size - uploadedBytes.value) / speed;
  return formatTime(remaining);
});

// 初始化
onMounted(async () => {
  await loadCategories();
});

// 加载分类
const loadCategories = async () => {
  try {
    const res = await getCategories();
    // request.js 的响应拦截器已经返回了 response.data，所以直接使用 res
    // 如果后端返回的是数组，直接使用；如果是对象，使用 res.data
    if (Array.isArray(res)) {
      categories.value = res;
    } else if (res && res.data) {
      categories.value = res.data;
    } else {
      categories.value = [];
    }

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

// 文件选择相关方法
const triggerVideoSelect = () => {
  videoInput.value?.click();
};

const triggerCoverSelect = () => {
  coverInput.value?.click();
};

const handleVideoSelect = (event) => {
  const file = event.target.files[0];
  if (!file) return;

  // 验证文件大小（最大 2GB）
  const maxSize = 2 * 1024 * 1024 * 1024;
  if (file.size > maxSize) {
    ElMessage.error("视频文件大小不能超过 2GB");
    return;
  }

  videoFile.value = file;
  videoPreviewUrl.value = URL.createObjectURL(file);

  // 自动填充标题（去掉扩展名）
  if (!videoForm.title) {
    videoForm.title = file.name.replace(/\.[^/.]+$/, "");
  }
};

const handleCoverSelect = (event) => {
  const file = event.target.files[0];
  if (!file) return;

  coverFile.value = file;
  coverPreviewUrl.value = URL.createObjectURL(file);
};

const handleSubtitleSelect = (file) => {
  subtitleFile.value = file.raw;
};

const handleSubtitleRemove = () => {
  subtitleFile.value = null;
};

const removeVideo = () => {
  videoFile.value = null;
  if (videoPreviewUrl.value) {
    URL.revokeObjectURL(videoPreviewUrl.value);
    videoPreviewUrl.value = "";
  }
  if (videoInput.value) {
    videoInput.value.value = "";
  }
};

const removeCover = () => {
  coverFile.value = null;
  if (coverPreviewUrl.value) {
    URL.revokeObjectURL(coverPreviewUrl.value);
    coverPreviewUrl.value = "";
  }
  if (coverInput.value) {
    coverInput.value.value = "";
  }
};

// 步骤控制
const nextStep = () => {
  currentStep.value++;
};

const prevStep = () => {
  currentStep.value--;
};

// 计算文件哈希（SHA-256）
const calculateFileHash = async (file) => {
  uploadStatus.value = "正在计算文件哈希...";
  uploadDetail.value = "用于秒传检测和断点续传";

  try {
    const buffer = await file.arrayBuffer();
    const hashBuffer = await crypto.subtle.digest("SHA-256", buffer);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    const hashHex = hashArray
      .map((b) => b.toString(16).padStart(2, "0"))
      .join("");
    return hashHex;
  } catch (error) {
    console.error("计算文件哈希失败:", error);
    throw new Error("计算文件哈希失败");
  }
};

// 开始上传
const startUpload = async () => {
  // 验证表单
  const valid = await videoFormRef.value?.validate().catch(() => false);
  if (!valid) return;

  currentStep.value = 2;
  uploading.value = true;
  uploadStartTime.value = Date.now();

  try {
    // 1. 计算文件哈希
    fileHash.value = await calculateFileHash(videoFile.value);

    // 2. 初始化上传
    uploadStatus.value = "初始化上传...";
    uploadDetail.value = "检查是否可以秒传";

    totalChunks.value = Math.ceil(videoFile.value.size / chunkSize);

    const initRes = await initUpload({
      file_hash: fileHash.value,
      file_name: videoFile.value.name,
      total_chunks: totalChunks.value,
      file_size: videoFile.value.size,
    });

    // request.js 的响应拦截器已经返回了 response.data，所以直接使用 initRes
    // 检查是否秒传（is_completed 为 true 且 video_id 存在表示秒传成功）
    if (initRes.is_completed && initRes.video_id) {
      uploadStatus.value = "秒传成功！";
      uploadDetail.value = "文件已存在，无需重新上传";
      uploadedChunks.value = totalChunks.value;
      uploadComplete.value = true;
      uploading.value = false;
      ElMessage.success("视频秒传成功！");
      return;
    }

    // 3. 获取已上传分片
    const uploadedList = initRes.uploaded_chunks || [];
    uploadedChunks.value = uploadedList.length;
    uploadedBytes.value = uploadedChunks.value * chunkSize;

    // 4. 上传分片
    await uploadChunks(uploadedList);

    // 5. 完成上传
    await completeUpload();
  } catch (error) {
    console.error("上传失败:", error);
    ElMessage.error(error.message || "上传失败");
    uploading.value = false;
    uploadStatus.value = "上传失败";
    uploadDetail.value = error.message || "请重试";
  }
};

// 上传分片
const uploadChunks = async (uploadedList) => {
  uploadStatus.value = "正在上传视频...";

  for (let i = 0; i < totalChunks.value; i++) {
    // 跳过已上传的分片
    if (uploadedList.includes(i)) {
      continue;
    }

    // 检查是否暂停
    if (!uploading.value) {
      throw new Error("上传已暂停");
    }

    const start = i * chunkSize;
    const end = Math.min(start + chunkSize, videoFile.value.size);
    const chunk = videoFile.value.slice(start, end);

    uploadDetail.value = `正在上传第 ${i + 1} / ${totalChunks.value} 个分片`;

    try {
      await uploadChunk(fileHash.value, i, chunk);
      uploadedChunks.value++;
      uploadedBytes.value += chunk.size;
    } catch (error) {
      console.error(`分片 ${i} 上传失败:`, error);
      throw new Error(`分片 ${i} 上传失败`);
    }
  }
};

// 完成上传
const completeUpload = async () => {
  uploadStatus.value = "正在完成上传...";
  uploadDetail.value = "合并分片并创建视频记录";

  try {
    // 完成上传（先创建视频，获取 video_id）
    const res = await finishUpload({
      file_hash: fileHash.value,
      title: videoForm.title,
      description: videoForm.description,
      category_id: videoForm.category_id,
      cover_url: "",
    });

    // request.js 会将响应包装为 { success: true, data: {...} }
    // 如果后端返回的对象包含 success 字段，则直接使用
    const videoRes = res.data || res;
    const videoId = videoRes?.video_id;
    if (!videoId) {
      console.error("finishUpload 响应:", res);
      throw new Error("未获取到视频ID，请稍后重试");
    }

    // 上传封面（如果有）
    if (coverFile.value) {
      uploadStatus.value = "正在上传封面...";
      uploadDetail.value = "请勿关闭窗口";
      await uploadVideoCover(videoId, coverFile.value);
    }

    // 上传字幕（如果有）
    if (subtitleFile.value) {
      uploadStatus.value = "正在上传字幕...";
      uploadDetail.value = "支持 SRT、VTT、JSON、ASS";
      await uploadVideoSubtitle(videoId, subtitleFile.value);
    }

    uploadStatus.value = "上传完成！";
    uploadDetail.value = "视频正在转码中，稍后即可观看";
    uploadComplete.value = true;
    uploading.value = false;

    ElMessage.success("视频上传成功！");
  } catch (error) {
    console.error("完成上传失败:", error);
    throw error;
  }
};

// 暂停上传
const pauseUpload = () => {
  uploading.value = false;
  uploadStatus.value = "上传已暂停";
  uploadDetail.value = '点击"继续上传"可恢复';
};

// 继续上传
const resumeUpload = async () => {
  uploading.value = true;
  uploadStartTime.value = Date.now();

  try {
    // 获取已上传分片
    const progressRes = await getUploadProgress(fileHash.value);
    // request.js 的响应拦截器已经返回了 response.data，所以直接使用 progressRes
    const uploadedList = progressRes.uploaded_chunks || [];
    uploadedChunks.value = uploadedList.length;
    uploadedBytes.value = uploadedChunks.value * chunkSize;

    // 继续上传
    await uploadChunks(uploadedList);
    await completeUpload();
  } catch (error) {
    console.error("继续上传失败:", error);
    ElMessage.error("继续上传失败");
    uploading.value = false;
  }
};

// 返回首页
const goToHome = () => {
  router.push("/");
};

// 继续上传
const uploadAnother = () => {
  // 重置所有状态
  currentStep.value = 0;
  videoFile.value = null;
  coverFile.value = null;
  subtitleFile.value = null;
  videoPreviewUrl.value = "";
  coverPreviewUrl.value = "";
  videoForm.title = "";
  videoForm.description = "";
  videoForm.category_id = null;
  uploading.value = false;
  uploadComplete.value = false;
  uploadStatus.value = "准备上传...";
  uploadDetail.value = "";
  fileHash.value = "";
  totalChunks.value = 0;
  uploadedChunks.value = 0;
  uploadStartTime.value = 0;
  uploadedBytes.value = 0;
};

// 工具函数
const formatFileSize = (bytes) => {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return (bytes / Math.pow(k, i)).toFixed(2) + " " + sizes[i];
};

const formatSpeed = (bytesPerSecond) => {
  if (bytesPerSecond === 0) return "0 KB/s";
  const k = 1024;
  const sizes = ["B/s", "KB/s", "MB/s"];
  const i = Math.floor(Math.log(bytesPerSecond) / Math.log(k));
  return (bytesPerSecond / Math.pow(k, i)).toFixed(2) + " " + sizes[i];
};

const formatTime = (seconds) => {
  if (seconds < 60) return `${Math.floor(seconds)} 秒`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)} 分钟`;
  return `${Math.floor(seconds / 3600)} 小时`;
};
</script>

<style scoped>
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

/* 步骤内容 */
.step-content {
  margin-top: var(--spacing-2xl);
  background: var(--bg-white);
  border-radius: var(--radius-lg);
  padding: var(--spacing-2xl);
  box-shadow: var(--shadow-sm);
}

/* 上传区域 */
.upload-area {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xl);
}

.file-upload-box {
  border: 2px dashed var(--border-base);
  border-radius: var(--radius-lg);
  padding: var(--spacing-2xl);
  cursor: pointer;
  transition: all var(--transition-base);
}

.file-upload-box:hover {
  border-color: var(--primary-color);
  background: var(--primary-light);
}

.upload-placeholder {
  text-align: center;
  padding: var(--spacing-2xl) 0;
}

.upload-placeholder.small {
  padding: var(--spacing-lg) 0;
}

.upload-text {
  font-size: var(--font-size-lg);
  color: var(--text-primary);
  margin: var(--spacing-md) 0 var(--spacing-sm);
}

.upload-hint {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}

.file-preview {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.video-preview {
  width: 100%;
  max-height: 400px;
  border-radius: var(--radius-md);
}

.file-info {
  text-align: center;
}

.file-name {
  font-size: var(--font-size-base);
  color: var(--text-primary);
  margin-bottom: var(--spacing-xs);
}

.file-size {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  margin-bottom: var(--spacing-md);
}

/* 封面上传 */
.cover-upload-section h3,
.subtitle-upload-section h3 {
  font-size: var(--font-size-lg);
  margin-bottom: var(--spacing-md);
  color: var(--text-primary);
}

.cover-upload-box {
  width: 300px;
  height: 200px;
  border: 2px dashed var(--border-base);
  border-radius: var(--radius-md);
  cursor: pointer;
  overflow: hidden;
  position: relative;
  transition: all var(--transition-base);
}

.cover-upload-box:hover {
  border-color: var(--primary-color);
}

.cover-preview {
  width: 100%;
  height: 100%;
  position: relative;
}

.cover-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.remove-btn {
  position: absolute;
  top: var(--spacing-sm);
  right: var(--spacing-sm);
}

/* 表单 */
.video-form {
  max-width: 600px;
  margin: 0 auto;
}

/* 上传进度 */
.upload-progress-section {
  text-align: center;
}

.progress-info h3 {
  font-size: var(--font-size-xl);
  color: var(--text-primary);
  margin-bottom: var(--spacing-sm);
}

.progress-detail {
  font-size: var(--font-size-base);
  color: var(--text-secondary);
  margin-bottom: var(--spacing-xl);
}

.progress-bar-wrapper {
  margin: var(--spacing-2xl) 0;
}

.progress-details {
  display: flex;
  justify-content: space-around;
  margin: var(--spacing-xl) 0;
  padding: var(--spacing-lg);
  background: var(--bg-light);
  border-radius: var(--radius-md);
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.detail-item .label {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}

.detail-item .value {
  font-size: var(--font-size-lg);
  font-weight: 600;
  color: var(--text-primary);
}

/* 操作按钮 */
.step-actions {
  display: flex;
  justify-content: center;
  gap: var(--spacing-md);
  margin-top: var(--spacing-2xl);
}

/* 响应式 */
@media (max-width: 768px) {
  .upload-container {
    padding: 0 var(--spacing-md);
  }

  .step-content {
    padding: var(--spacing-lg);
  }

  .cover-upload-box {
    width: 100%;
  }

  .progress-details {
    flex-direction: column;
    gap: var(--spacing-md);
  }
}
</style>
