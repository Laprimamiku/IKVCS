/**
 * 通用表单处理 Composable
 * 提取表单相关的通用逻辑（验证、提交、重置等）
 */
import { ref, reactive, type Ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'

export interface UseFormOptions<T> {
  initialValues: T
  rules?: FormRules<T>
  onSubmit: (values: T) => Promise<void> | void
  onSuccess?: () => void
  onError?: (error: unknown) => void
  successMessage?: string
  errorMessage?: string
}

export function useForm<T extends Record<string, unknown>>(options: UseFormOptions<T>) {
  const {
    initialValues,
    rules,
    onSubmit,
    onSuccess,
    onError,
    successMessage = '操作成功',
    errorMessage = '操作失败'
  } = options

  const formRef = ref<FormInstance | null>(null)
  const submitting = ref(false)
  const formData = reactive<T>({ ...initialValues } as T)

  const validate = async (): Promise<boolean> => {
    if (!formRef.value) return false
    
    try {
      await formRef.value.validate()
      return true
    } catch {
      return false
    }
  }

  const resetFields = () => {
    if (formRef.value) {
      formRef.value.resetFields()
    }
    Object.assign(formData, initialValues)
  }

  const submit = async () => {
    if (!await validate()) {
      return false
    }

    submitting.value = true
    
    try {
      await onSubmit(formData)
      
      if (onSuccess) {
        onSuccess()
      } else {
        ElMessage.success(successMessage)
      }
      
      return true
    } catch (err) {
      console.error(errorMessage, err)
      
      if (onError) {
        onError(err)
      } else {
        ElMessage.error(errorMessage)
      }
      
      return false
    } finally {
      submitting.value = false
    }
  }

  return {
    formRef,
    formData,
    submitting,
    rules,
    validate,
    resetFields,
    submit
  }
}














