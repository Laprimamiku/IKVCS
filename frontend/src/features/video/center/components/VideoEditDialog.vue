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
      <el-form-item label="人工字幕">
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
              {{ form.subtitle_url ? "更换人工字幕" : "上传人工字幕" }}
            </el-button>
            <template #tip>
              <div class="el-upload__tip">
                支持 SRT、VTT、JSON、ASS 格式（可选）
              </div>
            </template>
          </el-upload>
        </div>
      </el-form-item>

      <!-- 音频转字幕 -->
      <el-form-item label="AI字幕">
        <div class="subtitle-upload-section">
          <div v-if="form.subtitle_audio_file" class="subtitle-preview">
            <el-icon><Document /></el-icon>
            <span>{{ form.subtitle_audio_file.name }}</span>
            <el-button type="danger" size="small" text @click="removeSubtitleAudio">
              移除
            </el-button>
          </div>
          <el-upload
            v-else
            :auto-upload="false"
            :show-file-list="false"
            accept=".mp3,.wav,.m4a,.aac,.flac,.ogg,.opus,.webm,.mp4"
            :on-change="handleSubtitleAudioChange"
            :disabled="subtitleAudioUploading"
          >
            <el-button type="primary" plain :loading="subtitleAudioUploading">
              <el-icon><Document /></el-icon>
              {{ form.subtitle_url ? "替换AI字幕（音频/视频转写）" : "AI字幕（音频/视频转写）" }}
            </el-button>
            <template #tip>
              <div class="el-upload__tip">
                支持 MP3、WAV、M4A、AAC、FLAC、OGG、OPUS、WEBM、MP4（生成 AI 字幕）
              </div>
            </template>
          </el-upload>
        </div>
      </el-form-item>

      <el-form-item label="字幕来源">
        <div class="subtitle-select-section">
          <el-select
            v-model="form.subtitle_selected_url"
            placeholder="选择展示字幕"
            style="width: 100%"
            :loading="subtitleLoading"
          >
            <el-option
              v-for="item in subtitleItems"
              :key="item.url"
              :label="formatSubtitleLabel(item)"
              :value="item.url"
            />
          </el-select>
          <div class="subtitle-select-meta">
            <span v-if="!subtitleItems.length">暂无字幕</span>
            <el-button size="small" text @click="fetchSubtitleList">刷新</el-button>
          </div>
        </div>
      </el-form-item>

      <!-- 标签管理 -->
      <el-form-item label="标签">
        <div class="tag-management-section">
          <div class="tag-input-row">
            <el-input
              v-model="newTagName"
              placeholder="输入标签名称，按回车添加"
              maxlength="50"
              @keyup.enter="handleAddTag"
              @blur="handleAddTag"
            >
              <template #append>
                <el-button @click="handleAddTag" :loading="tagAdding">添加</el-button>
              </template>
            </el-input>
          </div>
          <div class="tag-list" v-if="displayTags.length > 0">
            <el-tag
              v-for="tag in displayTags"
              :key="tag.id"
              :closable="true"
              @close="handleRemoveTag(tag.id!)"
              class="tag-item"
            >
              {{ tag.name }}
            </el-tag>
          </div>
          <div v-else class="tag-empty">
            <span class="empty-text">暂无标签，添加标签可以帮助其他用户发现您的视频</span>
          </div>
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
      <div class="dialog-footer">
        <el-button type="danger" @click="handleDelete">删除</el-button>
        <div class="footer-actions">
          <el-button @click="handleCancel">取消</el-button>
          <el-button type="primary" :loading="saving" @click="handleSave">
            保存
          </el-button>
        </div>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, watch, computed } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import type { FormInstance, FormRules, UploadFile } from "element-plus";
import { Picture, Document, Close, VideoCamera } from "@element-plus/icons-vue";
import type { Video, Category } from "@/shared/types/entity";
import type { VideoSubtitleItem } from "@/features/video/shared/api/video.api";
import { resolveFileUrl } from "@/shared/utils/urlHelpers";
import { initUpload, uploadChunk } from "@/features/video/upload/api/upload.api";
import { finishReupload, getVideoSubtitles, uploadVideoSubtitleAudio, addVideoTag, removeVideoTag, getVideoTags, type VideoTag } from "@/features/video/shared/api/video.api";
import { useFileHash } from "@/features/video/upload/composables/useFileHash";

// 定义保存数据的类型
interface SaveData {
  id: number;
  title: string;
  description: string;
  category_id: number | null;
  cover_file: File | null;
  subtitle_file: File | null;
  subtitle_audio_file: File | null;
  subtitle_selected_url: string | null;
}

const props = defineProps<{
  modelValue: boolean;
  video: Video | null;
  categories: Category[];
}>();

const emit = defineEmits<{
  "update:modelValue": [value: boolean];
  save: [data: SaveData];
  delete: [video: Video];
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
  subtitle_selected_url: string;
  subtitle_file: File | null;
  subtitle_audio_file: File | null;
}>({
  id: null,
  title: "",
  description: "",
  category_id: null,
  cover_url: "",
  cover_preview: "",
  cover_file: null,
  subtitle_url: "",
  subtitle_selected_url: "",
  subtitle_file: null,
  subtitle_audio_file: null,
});

const subtitleItems = ref<VideoSubtitleItem[]>([]);
const subtitleLoading = ref(false);
const subtitleAudioUploading = ref(false);

// 标签管理
const videoTags = ref<VideoTag[]>([]);
const newTagName = ref("");
const tagAdding = ref(false);

// 显示标签（不包含分类标签）
const displayTags = computed(() => {
  // 只显示用户添加的标签，不包含分类
  return videoTags.value;
});

const normalizeSubtitleUrl = (value: string) => {
  if (!value) return "";
  if (value.startsWith("/")) return value;
  try {
    const parsed = new URL(value);
    return parsed.pathname || value;
  } catch (error) {
    return value;
  }
};

const formatSubtitleLabel = (item: VideoSubtitleItem) => {
  const sourceMap: Record<string, string> = {
    manual: "人工字幕",
    ai: "AI字幕",
    legacy: "历史字幕"
  };
  const sourceLabel = sourceMap[item.source] || item.source;
  const suffix = item.exists === false ? " (missing)" : "";
  return `${sourceLabel} - ${item.filename}${suffix}`;
};

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

const fetchSubtitleList = async () => {
  if (!form.id) return;
  subtitleLoading.value = true;
  try {
    const res = await getVideoSubtitles(form.id);
    if (res.success) {
      subtitleItems.value = res.data.items || [];
      const activeUrl =
        res.data.active_url ||
        subtitleItems.value.find((item) => item.is_active)?.url ||
        "";
      const normalizedSelected = normalizeSubtitleUrl(form.subtitle_selected_url || "");
      if (!normalizedSelected) {
        form.subtitle_selected_url = activeUrl || normalizeSubtitleUrl(form.subtitle_url || "");
      } else if (
        activeUrl &&
        normalizedSelected !== activeUrl &&
        !subtitleItems.value.some((item) => item.url === normalizedSelected)
      ) {
        form.subtitle_selected_url = activeUrl;
      }
    }
  } catch (error) {
    console.error("加载字幕列表失败:", error);
  } finally {
    subtitleLoading.value = false;
  }
};

watch(
  () => props.modelValue,
  (val) => {
    visible.value = val;
    if (val && props.video) {
      form.id = props.video.id;
      form.title = props.video.title;
      form.description = props.video.description || "";
      form.category_id = props.video.category_id || props.video.category?.id || null;
      // 分类改变时，标签列表会自动更新（通过displayTags计算属性）
      form.cover_url = props.video.cover_url || "";
      form.cover_preview = props.video.cover_url
        ? resolveFileUrl(props.video.cover_url)
        : "";
      form.cover_file = null;
      form.subtitle_url = normalizeSubtitleUrl(props.video.subtitle_url || "");
      form.subtitle_selected_url = normalizeSubtitleUrl(props.video.subtitle_url || "");
      form.subtitle_file = null;
      form.subtitle_audio_file = null;
      subtitleItems.value = [];
      fetchSubtitleList();
      
      // 加载视频标签
      loadVideoTags();
      
      // 重置重新上传状态
      reuploading.value = false;
      reuploadProgress.value = 0;
      reuploadStatus.value = undefined;
      reuploadStatusText.value = "准备上传...";
      reuploadVideoFile.value = null;
      reuploadFileHash.value = "";
      
      // 重置标签输入
      newTagName.value = "";
      videoTags.value = [];
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
  form.subtitle_audio_file = null;
  form.subtitle_selected_url = "";
};

const removeSubtitle = () => {
  form.subtitle_file = null;
  if (!form.subtitle_selected_url) {
    form.subtitle_selected_url = form.subtitle_url || "";
  }
};

const handleSubtitleAudioChange = (file: UploadFile) => {
  if (!file.raw) return;
  const validExts = [".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".opus", ".webm", ".mp4"];
  const ext = "." + file.name.split(".").pop()?.toLowerCase();
  if (!ext || !validExts.includes(ext)) {
    ElMessage.warning("格式不支持，仅支持MP3、WAV、M4A、AAC、FLAC、OGG、OPUS、WEBM、MP4");
    return;
  }
  const startUpload = async () => {
    if (!form.id) return;
    subtitleAudioUploading.value = true;
    try {
      const response = await uploadVideoSubtitleAudio(form.id, file.raw!);
      const subtitleUrl = (response as any)?.data?.subtitle_url;
      if (subtitleUrl) {
        form.subtitle_url = subtitleUrl;
        form.subtitle_selected_url = subtitleUrl;
        form.subtitle_audio_file = null;
        await fetchSubtitleList();
        ElMessage.success("AI字幕生成成功");
      } else {
        ElMessage.error("AI字幕生成失败，请重试");
      }
    } catch (error: any) {
      console.error("AI字幕生成失败:", error);
      const errorMsg = error?.response?.data?.detail || error?.message || "AI字幕生成失败";
      ElMessage.error(errorMsg);
      form.subtitle_audio_file = null;
    } finally {
      subtitleAudioUploading.value = false;
    }
  };

  const hasExistingSubtitles = Boolean(form.subtitle_url) || subtitleItems.value.length > 0;
  if (hasExistingSubtitles) {
    ElMessageBox.confirm(
      "检测到已有字幕，继续将生成新的 AI 字幕并替换当前展示字幕，是否继续？",
      "AI字幕提示",
      { confirmButtonText: "继续", cancelButtonText: "取消", type: "warning" }
    )
      .then(startUpload)
      .catch(() => undefined);
    return;
  }

  startUpload();
};

const removeSubtitleAudio = () => {
  form.subtitle_audio_file = null;
  if (!form.subtitle_selected_url) {
    form.subtitle_selected_url = form.subtitle_url || "";
  }
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
    subtitle_audio_file: form.subtitle_audio_file,
    subtitle_selected_url: form.subtitle_selected_url || null,
  });
};

const handleCancel = () => {
  emit("cancel");
};

const handleDelete = async () => {
  if (!props.video) return;

  try {
    await ElMessageBox.confirm(
      `确定要删除视频"${props.video.title}"吗？此操作不可恢复。`,
      "删除确认",
      {
        confirmButtonText: "确定删除",
        cancelButtonText: "取消",
        type: "warning",
      }
    );
    emit("delete", props.video);
  } catch (error) {
    // 用户取消删除
  }
};

// 加载视频标签
const loadVideoTags = async () => {
  if (!form.id) return;
  try {
    const res = await getVideoTags(form.id);
    if (res.success && res.data) {
      videoTags.value = res.data.tags || [];
    }
  } catch (error) {
    console.error("加载视频标签失败:", error);
  }
};

// 添加标签
const handleAddTag = async () => {
  if (!form.id || !newTagName.value.trim()) return;
  
  const tagName = newTagName.value.trim();
  if (tagName.length === 0 || tagName.length > 50) {
    ElMessage.warning("标签名称长度应在1-50个字符之间");
    return;
  }
  
  // 检查是否已存在
  if (videoTags.value.some(t => t.name === tagName)) {
    ElMessage.warning("该标签已存在");
    newTagName.value = "";
    return;
  }
  
  tagAdding.value = true;
  try {
    const res = await addVideoTag(form.id, tagName);
    if (res.success && res.data) {
      videoTags.value.push({
        id: res.data.tag_id,
        name: res.data.tag_name
      });
      newTagName.value = "";
      ElMessage.success("标签添加成功");
    }
  } catch (error: any) {
    console.error("添加标签失败:", error);
    ElMessage.error(error?.response?.data?.detail || "添加标签失败");
  } finally {
    tagAdding.value = false;
  }
};

// 删除标签
const handleRemoveTag = async (tagId: number) => {
  if (!form.id) return;
  
  try {
    const res = await removeVideoTag(form.id, tagId);
    if (res.success) {
      videoTags.value = videoTags.value.filter(t => t.id !== tagId);
      ElMessage.success("标签删除成功");
    }
  } catch (error: any) {
    console.error("删除标签失败:", error);
    ElMessage.error(error?.response?.data?.detail || "删除标签失败");
  }
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
        subtitle_audio_file: form.subtitle_audio_file,
        subtitle_selected_url: form.subtitle_selected_url || null,
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

.subtitle-select-section {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.subtitle-select-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12px;
  color: var(--text-secondary);
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

.tag-management-section {
  width: 100%;
}

.tag-input-row {
  margin-bottom: var(--spacing-sm);
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-sm);
  margin-top: var(--spacing-sm);
}

.tag-item {
  margin: 0;
}

.tag-empty {
  margin-top: var(--spacing-sm);
  padding: var(--spacing-sm);
  text-align: center;
  color: var(--text-tertiary);
  font-size: 12px;
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

  .dialog-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--spacing-sm);
  }

  .footer-actions {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
  }
</style>
