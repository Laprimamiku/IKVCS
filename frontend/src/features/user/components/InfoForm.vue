<template>
  <div class="info-form-section">
    <el-form
      ref="formRef"
      :model="formData"
      :rules="rules"
      label-width="100px"
      label-position="left"
      class="form"
    >
      <el-form-item label="用户名">
        <el-input
          :model-value="userInfo.username"
          disabled
          class="input-disabled"
        />
        <span class="form-tip">用户名不可修改</span>
      </el-form-item>

      <el-form-item label="昵称" prop="nickname">
        <el-input
          v-model="formData.nickname"
          placeholder="默认使用用户名"
          maxlength="50"
          show-word-limit
          class="input"
        />
      </el-form-item>

      <el-form-item label="个人简介" prop="intro">
        <el-input
          v-model="formData.intro"
          type="textarea"
          placeholder="这个人很懒，什么都没有写~"
          :rows="4"
          maxlength="500"
          show-word-limit
          class="textarea"
        />
      </el-form-item>

      <el-form-item label="注册时间">
        <span class="info-text">{{ formatDate(userInfo.created_at) }}</span>
      </el-form-item>

      <el-form-item label="最后登录">
        <span class="info-text">{{ formatDate(userInfo.last_login_time) }}</span>
      </el-form-item>

      <el-form-item>
        <el-button
          type="primary"
          @click="handleSubmit"
          :loading="submitting"
          class="submit-btn"
        >
          <el-icon v-if="!submitting"><Check /></el-icon>
          <span>{{ submitting ? '保存中...' : '保存修改' }}</span>
        </el-button>
        <el-button
          @click="handleReset"
          class="reset-btn"
        >
          <el-icon><RefreshLeft /></el-icon>
          <span>重置</span>
        </el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, watch } from 'vue'
import { Check, RefreshLeft } from '@element-plus/icons-vue'
import type { FormInstance, FormRules } from 'element-plus'
import type { UserInfo } from "@/shared/types/entity"

const props = defineProps<{
  userInfo: UserInfo
  submitting: boolean
}>()

const emit = defineEmits<{
  submit: [data: { nickname: string; intro: string }]
}>()

const formRef = ref<FormInstance | null>(null)
const DEFAULT_INTRO = '这个人很懒，什么都没有写~'

const formData = reactive({
  nickname: '',
  intro: ''
})

const rules: FormRules = {
  nickname: [
    {
      validator: (_rule, value, callback) => {
        const normalized = String(value || '').trim()
        if (!normalized) {
          callback()
          return
        }
        if (normalized.length < 2 || normalized.length > 50) {
          callback(new Error('昵称长度在 2 到 50 个字符'))
          return
        }
        callback()
      },
      trigger: 'blur'
    }
  ],
  intro: [
    { max: 500, message: '简介长度不能超过 500 个字符', trigger: 'blur' }
  ]
}

const syncFormData = () => {
  formData.nickname = props.userInfo.nickname || props.userInfo.username || ''
  formData.intro = props.userInfo.intro || DEFAULT_INTRO
}

watch(
  () => [props.userInfo.username, props.userInfo.nickname, props.userInfo.intro],
  syncFormData,
  { immediate: true }
)

const formatDate = (dateStr?: string): string => {
  if (!dateStr) return '未知'
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN')
}

const handleSubmit = async () => {
  if (!formRef.value) return

  await formRef.value.validate((valid) => {
    if (valid) {
      emit('submit', {
        nickname: (formData.nickname || props.userInfo.username || '').trim(),
        intro: (formData.intro || DEFAULT_INTRO).trim()
      })
    }
  })
}

const handleReset = () => {
  syncFormData()
  formRef.value?.clearValidate()
}

defineExpose({
  setFormData: (data: { nickname: string; intro: string }) => {
    formData.nickname = data.nickname
    formData.intro = data.intro
  },
  resetForm: () => {
    syncFormData()
    formRef.value?.clearValidate()
  }
})
</script>

<style lang="scss" scoped>
.info-form-section {
  flex: 1;
}

.form :deep(.el-form-item__label) {
  font-weight: 600;
  color: var(--bili-text-1);
}

.input :deep(.el-input__wrapper) {
  border-radius: 8px;
  box-shadow: 0 0 0 1px var(--bili-border-1) inset;
  transition: all 0.3s;

  &:hover {
    box-shadow: 0 0 0 1px var(--bili-pink) inset;
  }

  &.is-focus {
    box-shadow: 0 0 0 2px var(--bili-pink) inset;
  }
}

.input-disabled :deep(.el-input__wrapper) {
  background: var(--bili-bg-2);
  cursor: not-allowed;
}

.textarea :deep(.el-textarea__inner) {
  border-radius: 8px;
  border: 1px solid var(--bili-border-1);
  transition: all 0.3s;

  &:hover {
    border-color: var(--bili-pink);
  }

  &:focus {
    border-color: var(--bili-pink);
    box-shadow: 0 0 0 2px rgba(251, 114, 153, 0.1);
  }
}

.form-tip {
  font-size: 12px;
  color: var(--bili-text-3);
  margin-left: 8px;
}

.info-text {
  font-size: 14px;
  color: var(--bili-text-2);
}

.submit-btn {
  background: var(--bili-pink);
  border: none;
  border-radius: 20px;
  padding: 10px 32px;

  &:hover {
    background: var(--bili-pink-hover);
  }
}

.reset-btn {
  border: 1px solid var(--bili-border-2);
  border-radius: 20px;
  padding: 10px 32px;

  &:hover {
    border-color: var(--bili-pink);
    color: var(--bili-pink);
  }
}
</style>