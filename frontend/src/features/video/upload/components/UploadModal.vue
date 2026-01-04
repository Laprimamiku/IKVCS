<template>
  <div v-if="modelValue" class="upload-modal-overlay" @click="handleClose">
    <div class="upload-modal" @click.stop>
      <div class="upload-modal-header">
        <h3>视频投稿</h3>
        <button class="close-btn" @click="handleClose">✕</button>
      </div>
      <div class="upload-modal-content">
        <!-- Steps Indicator -->
        <div class="steps-wrapper">
          <div class="steps-bar">
            <div 
              class="step-item" 
              :class="{ active: currentStep >= 0, completed: currentStep > 0 }"
            >
              <div class="step-circle">
                <span v-if="currentStep > 0">✓</span>
                <span v-else>1</span>
              </div>
              <span class="step-label">选择文件</span>
            </div>
            <div class="step-line" :class="{ active: currentStep > 0 }"></div>
            <div 
              class="step-item" 
              :class="{ active: currentStep >= 1, completed: currentStep > 1 }"
            >
              <div class="step-circle">
                <span v-if="currentStep > 1">✓</span>
                <span v-else>2</span>
              </div>
              <span class="step-label">填写信息</span>
            </div>
            <div class="step-line" :class="{ active: currentStep > 1 }"></div>
            <div 
              class="step-item" 
              :class="{ active: currentStep >= 2, completed: uploadComplete }"
            >
              <div class="step-circle">
                <span v-if="uploadComplete">✓</span>
                <span v-else>3</span>
              </div>
              <span class="step-label">上传完成</span>
            </div>
          </div>
        </div>

        <!-- Step Content -->
        <div class="step-content">
          <!-- Step 1: File Selection -->
          <div v-show="currentStep === 0" class="upload-step">
            <FileSelector
              :video-file="videoFile"
              :cover-file="coverFile"
              :subtitle-file="subtitleFile"
              :video-preview-url="videoPreviewUrl"
              :cover-preview-url="coverPreviewUrl"
              @video-selected="$emit('video-selected', $event)"
              @cover-selected="$emit('cover-selected', $event)"
              @subtitle-selected="$emit('subtitle-selected', $event)"
              @video-removed="$emit('video-removed')"
              @cover-removed="$emit('cover-removed')"
              @subtitle-removed="$emit('subtitle-removed')"
            />
            <div class="step-actions">
              <el-button
                type="primary"
                size="large"
                :disabled="!hasVideoFile"
                @click="$emit('next-step')"
              >
                下一步
              </el-button>
            </div>
          </div>

          <!-- Step 2: Video Info -->
          <div v-show="currentStep === 1" class="upload-step">
            <VideoInfoForm
              ref="videoFormRef"
              :categories="categories"
              :model-value="videoForm"
              @update:modelValue="$emit('video-form-update', $event)"
            />
            <div class="step-actions">
              <el-button size="large" @click="$emit('prev-step')">上一步</el-button>
              <el-button
                type="primary"
                size="large"
                :loading="uploading"
                @click="$emit('start-upload')"
              >
                开始上传
              </el-button>
            </div>
          </div>

          <!-- Step 3: Upload Progress -->
          <div v-show="currentStep === 2" class="upload-step">
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
              :cover-progress="coverProgress"
              :subtitle-progress="subtitleProgress"
              :cover-uploading="coverUploading"
              :subtitle-uploading="subtitleUploading"
              @resume="$emit('resume-upload')"
              @pause="$emit('pause-upload')"
              @go-home="$emit('go-home')"
              @upload-another="$emit('upload-another')"
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import FileSelector from "./FileSelector.vue";
import VideoInfoForm from "./VideoInfoForm.vue";
import UploadProgress from "./UploadProgress.vue";
import type { Category } from "@/shared/types/entity";

const props = defineProps<{
  modelValue: boolean;
  currentStep: number;
  videoFile: File | null;
  coverFile: File | null;
  subtitleFile: File | null;
  videoPreviewUrl: string | null;
  coverPreviewUrl: string | null;
  hasVideoFile: boolean;
  categories: Category[];
  videoForm: {
    title: string;
    description: string;
    category_id: number | null;
  };
  uploading: boolean;
  uploadComplete: boolean;
  uploadStatus: string;
  uploadDetail: string;
  totalProgress: number;
  uploadedChunks: number;
  totalChunks: number;
  uploadSpeed: string;
  remainingTime: string;
  coverProgress?: number;
  subtitleProgress?: number;
  coverUploading?: boolean;
  subtitleUploading?: boolean;
}>();

const emit = defineEmits<{
  (e: "update:modelValue", value: boolean): void;
  (e: "video-selected", file: File): void;
  (e: "cover-selected", file: File): void;
  (e: "subtitle-selected", file: File): void;
  (e: "video-removed"): void;
  (e: "cover-removed"): void;
  (e: "subtitle-removed"): void;
  (e: "next-step"): void;
  (e: "prev-step"): void;
  (e: "start-upload"): void;
  (e: "resume-upload"): void;
  (e: "pause-upload"): void;
  (e: "go-home"): void;
  (e: "upload-another"): void;
  (e: "video-form-update", value: { title: string; description: string; category_id: number | null }): void;
}>();

const videoFormRef = ref<InstanceType<typeof VideoInfoForm> | null>(null);

const handleClose = () => {
  emit("update:modelValue", false);
};

defineExpose({
  videoFormRef,
});
</script>

<style lang="scss" scoped>
.upload-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

.upload-modal {
  background: white;
  border-radius: 12px;
  width: 100%;
  max-width: 800px;
  max-height: 90vh;
  overflow: hidden;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

.upload-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid #e3e5e7;
  
  h3 {
    font-size: 18px;
    font-weight: 600;
    color: #18191c;
    margin: 0;
  }
  
  .close-btn {
    width: 32px;
    height: 32px;
    border: none;
    background: none;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    font-size: 18px;
    color: #61666d;
    transition: all 0.2s;
    
    &:hover {
      background: #f1f2f3;
      color: #18191c;
    }
  }
}

.upload-modal-content {
  padding: 32px 40px;
  max-height: calc(90vh - 80px);
  overflow-y: auto;
}

.steps-wrapper {
  margin-bottom: 32px;
}

.steps-bar {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0;
}

.step-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.step-circle {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #f1f2f3;
  color: #9499a0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  transition: all 0.3s;

  .step-item.active & {
    background: #00aeec;
    color: white;
    box-shadow: 0 4px 12px rgba(0, 174, 236, 0.3);
  }

  .step-item.completed & {
    background: #52c41a;
    color: white;
  }
}

.step-label {
  font-size: 13px;
  color: #9499a0;
  transition: color 0.3s;

  .step-item.active & {
    color: #00aeec;
    font-weight: 500;
  }

  .step-item.completed & {
    color: #52c41a;
  }
}

.step-line {
  width: 80px;
  height: 2px;
  background: #f1f2f3;
  margin: 0 16px;
  margin-bottom: 24px;
  border-radius: 1px;
  transition: background 0.3s;

  &.active {
    background: #00aeec;
  }
}

.step-content {
  animation: fadeIn 0.3s ease-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.upload-step {
  min-height: 450px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.step-actions {
  display: flex;
  justify-content: center;
  gap: 16px;
  margin-top: auto;
  padding-top: 32px;
  padding-bottom: 8px;
  border-top: 1px solid #f1f2f3;
}

@media (max-width: 768px) {
  .upload-modal {
    margin: 10px;
    max-width: none;
  }
  
  .upload-modal-content {
    padding: 16px;
  }
  
  .step-line {
    width: 60px;
    margin: 0 12px;
  }
}
</style>

