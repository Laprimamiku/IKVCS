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
import { ElMessage } from "element-plus";
import type { FormInstance, FormRules, UploadFile } from "element-plus";
import { Picture, Document, Close } from "@element-plus/icons-vue";
import type { Video, Category } from "@/shared/types/entity";
import { resolveFileUrl } from "@/shared/utils/urlHelpers";

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
</style>
