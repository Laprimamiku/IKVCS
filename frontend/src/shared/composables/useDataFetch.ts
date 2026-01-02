/**
 * 通用数据获取 Composable
 * 提取数据获取相关的通用逻辑（加载状态、错误处理等）
 */
import { ref, type Ref } from 'vue'
import { ElMessage } from 'element-plus'

export interface UseDataFetchOptions<T> {
  fetcher: () => Promise<T>
  immediate?: boolean
  onSuccess?: (data: T) => void
  onError?: (error: unknown) => void
  errorMessage?: string
}

export function useDataFetch<T>(options: UseDataFetchOptions<T>) {
  const {
    fetcher,
    immediate = true,
    onSuccess,
    onError,
    errorMessage = '数据加载失败'
  } = options

  const loading = ref(false)
  const error = ref<unknown>(null)
  const data = ref<T | null>(null) as Ref<T | null>

  const fetchData = async () => {
    loading.value = true
    error.value = null
    
    try {
      const result = await fetcher()
      data.value = result
      
      if (onSuccess) {
        onSuccess(result)
      }
      
      return result
    } catch (err) {
      error.value = err
      console.error(errorMessage, err)
      
      if (onError) {
        onError(err)
      } else {
        ElMessage.error(errorMessage)
      }
      
      throw err
    } finally {
      loading.value = false
    }
  }

  const reset = () => {
    loading.value = false
    error.value = null
    data.value = null
  }

  // 立即执行（如果需要）
  if (immediate) {
    fetchData()
  }

  return {
    loading,
    error,
    data,
    fetchData,
    reset
  }
}





