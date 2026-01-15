/**
 * 统一错误处理 Composable
 * 提供统一的错误处理逻辑和错误消息显示
 */
import { ElMessage, ElNotification } from 'element-plus'
import type { ApiResponse } from '@/shared/types/entity'

export interface ErrorHandlerOptions {
  /** 是否显示错误提示（默认 true） */
  showMessage?: boolean
  /** 是否显示错误通知（默认 false） */
  showNotification?: boolean
  /** 自定义错误消息前缀 */
  messagePrefix?: string
  /** 静默模式（不显示任何错误提示） */
  silent?: boolean
}

/**
 * 统一错误处理 Composable
 * 
 * @example
 * ```ts
 * const { handleError, handleApiError } = useErrorHandler({
 *   messagePrefix: '操作失败'
 * })
 * 
 * try {
 *   await someApiCall()
 * } catch (error) {
 *   handleError(error)
 * }
 * 
 * // 或者处理 API 响应
 * const response = await someApiCall()
 * if (!response.success) {
 *   handleApiError(response)
 * }
 * ```
 */
export function useErrorHandler(options: ErrorHandlerOptions = {}) {
  const {
    showMessage = true,
    showNotification = false,
    messagePrefix = '',
    silent = false
  } = options

  /**
   * 处理通用错误
   */
  const handleError = (error: unknown, customMessage?: string): void => {
    if (silent) return

    let errorMessage = customMessage || '操作失败'

    if (error instanceof Error) {
      errorMessage = error.message || errorMessage
    } else if (typeof error === 'string') {
      errorMessage = error
    }

    const finalMessage = messagePrefix ? `${messagePrefix}: ${errorMessage}` : errorMessage

    if (showNotification) {
      ElNotification.error({
        title: '错误',
        message: finalMessage,
        duration: 3000
      })
    } else if (showMessage) {
      ElMessage.error(finalMessage)
    }

    // 开发环境下输出到控制台
    if (import.meta.env.DEV) {
      console.error('Error handled:', error)
    }
  }

  /**
   * 处理 API 响应错误
   */
  const handleApiError = (response: ApiResponse<any>, customMessage?: string): void => {
    if (silent) return

    const errorMessage = customMessage || response.message || '操作失败'
    const finalMessage = messagePrefix ? `${messagePrefix}: ${errorMessage}` : errorMessage

    if (showNotification) {
      ElNotification.error({
        title: '请求失败',
        message: finalMessage,
        duration: 3000
      })
    } else if (showMessage) {
      ElMessage.error(finalMessage)
    }

    // 开发环境下输出到控制台
    if (import.meta.env.DEV) {
      console.error('API error:', response)
    }
  }

  /**
   * 处理网络错误
   */
  const handleNetworkError = (error: unknown): void => {
    if (silent) return

    const errorMessage = '网络连接失败，请检查网络后重试'

    if (showNotification) {
      ElNotification.error({
        title: '网络错误',
        message: errorMessage,
        duration: 3000
      })
    } else if (showMessage) {
      ElMessage.error(errorMessage)
    }

    // 开发环境下输出到控制台
    if (import.meta.env.DEV) {
      console.error('Network error:', error)
    }
  }

  return {
    handleError,
    handleApiError,
    handleNetworkError
  }
}

