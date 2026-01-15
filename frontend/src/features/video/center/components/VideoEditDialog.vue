<template>
  <el-dialog
    v-model="visible"
    title="编辑视频"
    width="700px"
    :close-on-click-modal="false"
  >
    <el-form :model="form" :rules="rules" ref="formRef" label-width="80px">
      <el-form-item label="标题" prop="title">
        <el-input
          v-model="form.title"
          placeholder="请输入视频标题"
          maxlength="100"
          show-word-limit
        />
      </el-form-item>

      <el-form-item label="描述" prop="description">
        <el-input
          v-model="form.description"
          type="textarea"
          :rows="4"
          placeholder="请输入视频描述（可选）"
          maxlength="500"
          show-word-limit
        />
      </el-form-item>

      <el-form-item label="分类" prop="category_id">
        <el-select
          v-model="form.category_id"
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

      <!-- 封面上传 -->
      <el-form-item label="封面">
        <div class="cover-upload-section">
          <div v-if="form.cover_preview" class="cover-preview">
            <img :src="form.cover_preview" alt="封面预览" />
            <el-button
              type="danger"
              size="small"
              circle
              class="remove-cover-btn"
              @click="removeCover"
            >
              <el-icon><Close /></el-icon>
            </el-button>
          </div>
          <el-upload
            v-else
            :auto-upload="false"
            :show-file-list="false"
            accept="image/*"
            :on-change="handleCoverChange"
          >
            <el-button type="primary" plain>
              <el-icon><Picture /></el-icon>
              {{ form.cover_url ? "更换封面" : "上传封面" }}
            </el-button>
            <template #tip>
              <div class="el-upload__tip">
                支持 JPG、PNG、WEBP 格式，最大 5MB
              </div>
            </template>
          </el-upload>
        </div>
      </el-form-item>

      <!-- 字幕上传 -->
      <el-form-item label="字幕">
        <div class="subtitle-upload-section">
          <div v-if="form.subtitle_file" class="subtitle-preview">
            <el-icon><Document /></el-icon>
            <span>{{ form.subtitle_file.name }}</span>
            <el-button type="danger" size="small" text @click="removeSubtitle">
              移除
            </el-button>
          </div>
          <el-upload
            v-else
            :auto-upload="false"
            :show-file-list="false"
            accept=".srt,.vtt,.json,.ass"
            :on-change="handleSubtitleChange"
          >
            <el-button type="primary" plain>
              <el-icon><Document /></el-icon>
              {{ form.subtitle_url ? "更换字幕" : "上传字幕" }}
            </el-button>
            <template #tip>
              <div class="el-upload__tip">
                支持 SRT、VTT、JSON、ASS 格式（可选）
              </div>
            </template>
          </el-upload>
        </div>
      </el-form-item>

      <!-- 视频重新上传 -->
      <el-form-item label="视频">
        <div class="video-reupload-section">
          <div v-if="reuploading" class="reupload-progress">
            <el-progress
              :percentage="reuploadProgress"
              :status="reuploadStatus"
              :format="() => reuploadStatusText"
            />
            <el-button
              v-if="reuploadStatus === 'success'"
              type="primary"
              size="small"
              @click="handleReuploadComplete"
            >
              完成
            </el-button>
          </div>
          <el-upload
            v-else
            :auto-upload="false"
            :show-file-list="false"
            accept="video/*"
            :on-change="handleVideoChange"
          >
            <el-button type="warning" plain>
              <el-icon><VideoCamera /></el-icon>
              重新上传视频
            </el-button>
            <template #tip>
              <div class="el-upload__tip">
                如果视频无法播放，可以重新上传视频文件（将替换现有视频）
              </div>
            </template>
          </el-upload>
        </div>
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="handleCancel">取消</el-button>
      <el-button type="primary" :loading="saving" @click="handleSave"
        >保存</el-button
      >
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import type { FormInstance, FormRules, UploadFile } from "element-plus";
import { Picture, Document, Close, VideoCamera } from "@element-plus/icons-vue";
import type { Video, Category } from "@/shared/types/entity";
import { resolveFileUrl } from "@/shared/utils/urlHelpers";
import { initUpload, uploadChunk } from "@/features/video/upload/api/upload.api";
import { finishReupload } from "@/features/video/shared/api/video.api";
import { useFileHash } from "@/features/video/upload/composables/useFileHash";

// 定义保存数据的类型
interface SaveData {
  id: number;
  title: string;
  description: string;
  category_id: number | null;
  cover_file: File | null;
  subtitle_file: File | null;
}

const props = defineProps<{
  modelValue: boolean;
  video: Video | null;
  categories: Category[];
}>();

const emit = defineEmits<{
  "update:modelValue": [value: boolean];
  save: [data: SaveData];
  cancel: [];
}>();

const visible = ref(false);
const formRef = ref<FormInstance>();
const saving = ref(false);

const form = reactive<{
  id: number | null;
  title: string;
  description: string;
  category_id: number | null;
  cover_url: string;
  cover_preview: string;
  cover_file: File | null;
  subtitle_url: string;
  subtitle_file: File | null;
}>({
  id: null,
  title: "",
  description: "",
  category_id: null,
  cover_url: "",
  cover_preview: "",
  cover_file: null,
  subtitle_url: "",
  subtitle_file: null,
});

// 重新上传相关状态
const reuploading = ref(false);
const reuploadProgress = ref(0);
const reuploadStatus = ref<"success" | "exception" | "warning" | undefined>(undefined);
const reuploadStatusText = ref("准备上传...");
const reuploadVideoFile = ref<File | null>(null);
const reuploadFileHash = ref<string>("");
const { calculateFileHash } = useFileHash();
const CHUNK_SIZE = 5 * 1024 * 1024; // 5MB

const rules: FormRules = {
  title: [
    { required: true, message: "请输入视频标题", trigger: "blur" },
    {
      min: 1,
      max: 100,
      message: "标题长度在 1 到 100 个字符",
      trigger: "blur",
    },
  ],
  category_id: [{ required: true, message: "请选择分类", trigger: "change" }],
  description: [
    { max: 500, message: "描述长度不能超过 500 个字符", trigger: "blur" },
  ],
};

watch(
  () => props.modelValue,
  (val) => {
    visible.value = val;
    if (val && props.video) {
      form.id = props.video.id;
      form.title = props.video.title;
      form.description = props.video.description || "";
      form.category_id = props.video.category_id || null;
      form.cover_url = props.video.cover_url || "";
      form.cover_preview = props.video.cover_url
        ? resolveFileUrl(props.video.cover_url)
        : "";
      form.cover_file = null;
      form.subtitle_url = props.video.subtitle_url || "";
      form.subtitle_file = null;
      
      // 重置重新上传状态
      reuploading.value = false;
      reuploadProgress.value = 0;
      reuploadStatus.value = undefined;
      reuploadStatusText.value = "准备上传...";
      reuploadVideoFile.value = null;
      reuploadFileHash.value = "";
    }
  }
);

watch(visible, (val) => {
  if (!val) {
    emit("update:modelValue", false);
  }
});

const handleCoverChange = (file: UploadFile) => {
  if (!file.raw) return;
  const validTypes = ["image/jpeg", "image/jpg", "image/png", "image/webp"];
  if (!validTypes.includes(file.raw.type)) {
    ElMessage.warning("封面格式不支持，仅支持 JPG、PNG、WEBP");
    return;
  }
  if (file.raw.size > 5 * 1024 * 1024) {
    ElMessage.warning("封面文件过大，最大 5MB");
    return;
  }
  form.cover_file = file.raw;
  const reader = new FileReader();
  reader.onload = (e) => {
    form.cover_preview = (e.target?.result as string) || "";
  };
  reader.readAsDataURL(file.raw);
};

const removeCover = () => {
  form.cover_file = null;
  form.cover_preview = "";
  form.cover_url = "";
};

const handleSubtitleChange = (file: UploadFile) => {
  if (!file.raw) return;
  const validExts = [".srt", ".vtt", ".json", ".ass"];
  const ext = "." + file.name.split(".").pop()?.toLowerCase();
  if (!ext || !validExts.includes(ext)) {
    ElMessage.warning("字幕格式不支持，仅支持 SRT、VTT、JSON、ASS");
    return;
  }
  form.subtitle_file = file.raw;
};

const removeSubtitle = () => {
  form.subtitle_file = null;
  form.subtitle_url = "";
};

const handleVideoChange = async (file: UploadFile) => {
  if (!file.raw || !form.id) return;
  
  const validTypes = ["video/mp4", "video/quicktime", "video/x-msvideo", "video/webm"];
  if (!validTypes.includes(file.raw.type)) {
    ElMessage.warning("视频格式不支持，仅支持 MP4、MOV、AVI、WEBM");
    return;
  }
  
  try {
    await ElMessageBox.confirm(
      "重新上传视频将替换现有视频文件，此操作不可撤销。是否继续？",
      "确认重新上传",
      {
        confirmButtonText: "确认",
        cancelButtonText: "取消",
        type: "warning",
      }
    );
    
    reuploadVideoFile.value = file.raw;
    reuploading.value = true;
    reuploadProgress.value = 0;
    reuploadStatus.value = undefined;
    reuploadStatusText.value = "正在计算文件哈希...";
    
    // 计算文件哈希
    const hash = await calculateFileHash(file.raw);
    reuploadFileHash.value = hash;
    
    // 开始上传
    await startReupload(file.raw, hash);
  } catch (error: any) {
    if (error !== "cancel") {
      console.error("选择视频文件失败:", error);
      ElMessage.error("选择视频文件失败，请重试");
    }
    reuploadVideoFile.value = null;
    reuploading.value = false;
  }
};

const startReupload = async (file: File, hash: string) => {
  try {
    // 1. 初始化上传
    reuploadStatusText.value = "初始化上传...";
    const chunks = Math.ceil(file.size / CHUNK_SIZE);
    const initResponse = await initUpload({
      file_hash: hash,
      file_name: file.name,
      total_chunks: chunks,
      file_size: file.size,
    });
    
    const initData = (initResponse as any)?.data || initResponse;
    
    // 检查是否秒传
    if (initData.is_completed && initData.video_id) {
      reuploadStatusText.value = "秒传成功！";
      reuploadProgress.value = 100;
      reuploadStatus.value = "success";
      ElMessage.success("视频秒传成功！");
      return;
    }
    
    // 2. 上传分片
    const totalChunks = initData.total_chunks || chunks;
    const uploadedChunks = initData.uploaded_chunks || [];
    
    reuploadStatusText.value = `开始上传分片 (${uploadedChunks.length}/${totalChunks})...`;
    
    for (let i = 0; i < totalChunks; i++) {
      // 跳过已上传的分片
      if (uploadedChunks.includes(i)) {
        continue;
      }
      
      const start = i * CHUNK_SIZE;
      const end = Math.min(start + CHUNK_SIZE, file.size);
      const chunk = file.slice(start, end);
      
      reuploadStatusText.value = `正在上传分片 ${i + 1}/${totalChunks}...`;
      
      await uploadChunk(hash, i, chunk);
      
      const progress = Math.floor(((i + 1) / totalChunks) * 100);
      reuploadProgress.value = progress;
    }
    
    // 3. 完成上传
    reuploadStatusText.value = "正在完成上传...";
    await finishReupload(form.id!, hash);
    
    reuploadProgress.value = 100;
    reuploadStatus.value = "success";
    reuploadStatusText.value = "重新上传成功！视频正在转码中...";
    ElMessage.success("视频重新上传成功，正在转码中");
  } catch (error: any) {
    console.error("重新上传失败:", error);
    reuploadStatus.value = "exception";
    reuploadStatusText.value = `上传失败: ${error?.response?.data?.detail || error?.message || "未知错误"}`;
    ElMessage.error("重新上传失败，请重试");
  }
};

const handleReuploadComplete = () => {
  reuploading.value = false;
  reuploadProgress.value = 0;
  reuploadStatus.value = undefined;
  reuploadStatusText.value = "准备上传...";
  reuploadVideoFile.value = null;
  reuploadFileHash.value = "";
  emit("save", {
    id: form.id!,
    title: form.title,
    description: form.description,
    category_id: form.category_id,
    cover_file: form.cover_file,
    subtitle_file: form.subtitle_file,
  });
};

const handleCancel = () => {
  emit("cancel");
};

const handleSave = async () => {
  if (!formRef.value || !form.id) return;

  await formRef.value.validate(async (valid) => {
    if (!valid) return;

    saving.value = true;
    try {
      emit("save", {
        id: form.id!,
        title: form.title,
        description: form.description,
        category_id: form.category_id,
        cover_file: form.cover_file,
        subtitle_file: form.subtitle_file,
      });
    } finally {
      saving.value = false;
    }
  });
};
</script>

<style lang="scss" scoped>
.cover-upload-section,
.subtitle-upload-section {
  width: 100%;
}

.cover-preview {
  position: relative;
  width: 200px;
  height: 112px;
  border-radius: var(--radius-md);
  overflow: hidden;
  margin-bottom: var(--spacing-sm);
}

.cover-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.remove-cover-btn {
  position: absolute;
  top: 4px;
  right: 4px;
}

.subtitle-preview {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm);
  background: var(--bg-light);
  border-radius: var(--radius-base);
}

.video-reupload-section {
  width: 100%;
}

.reupload-progress {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}
</style>
