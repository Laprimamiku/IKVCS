<template>
  <el-dialog
    v-model="dialogVisible"
    title="裁剪头像"
    width="600px"
    :before-close="handleClose"
    class="avatar-cropper-dialog"
  >
    <div class="cropper-container">
      <vue-cropper
        ref="cropperRef"
        :img="imgSrc"
        :output-size="1"
        :output-type="outputType"
        :info="true"
        :full="false"
        :can-move="true"
        :can-move-box="true"
        :fixed-box="false"
        :original="false"
        :auto-crop="true"
        :auto-crop-width="200"
        :auto-crop-height="200"
        :center-box="true"
        :high="true"
        :fixed="true"
        :fixed-number="[1, 1]"
      />
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="handleClose">取消</el-button>
        <el-button type="primary" @click="handleConfirm" :loading="uploading">
          {{ uploading ? '上传中...' : '确定' }}
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
/**
 * 头像裁剪组件
 * 
 * 功能：
 * 1. 图片裁剪
 * 2. 实时预览
 * 3. 上传裁剪后的图片
 */
import { ref, watch } from 'vue'
import { VueCropper } from 'vue-cropper'
import 'vue-cropper/dist/index.css'

type CropperInstance = {
  getCropBlob: (cb: (blob: Blob) => void) => void
}

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  imgSrc: {
    type: String,
    default: ''
  },
  outputType: {
    type: String,
    default: 'png'
  }
})

const emit = defineEmits(['update:modelValue', 'confirm'])

const dialogVisible = ref(props.modelValue)
const cropperRef = ref<CropperInstance | null>(null)
const uploading = ref(false)

// 监听 modelValue 变化
watch(() => props.modelValue, (val) => {
  dialogVisible.value = val
})

// 监听 dialogVisible 变化
watch(dialogVisible, (val) => {
  emit('update:modelValue', val)
})

/**
 * 关闭对话框
 */
const handleClose = () => {
  dialogVisible.value = false
}

/**
 * 确认裁剪
 */
const handleConfirm = () => {
  if (!cropperRef.value) return

  uploading.value = true
  
  // 获取裁剪后的图片（Blob 格式）
  cropperRef.value.getCropBlob((blob) => {
    // 将 Blob 转换为 File 对象
    const file = new File([blob], `avatar.${props.outputType}`, {
      type: `image/${props.outputType}`
    })
    
    // 触发确认事件
    emit('confirm', file)
    
    uploading.value = false
    dialogVisible.value = false
  })
}
</script>

<style lang="scss" scoped>
.avatar-cropper-dialog :deep(.el-dialog__body) {
  padding: 20px;
}

.cropper-container {
  width: 100%;
  height: 400px;
  background: #f5f7fa;
  border-radius: 8px;
  overflow: hidden;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
</style>
