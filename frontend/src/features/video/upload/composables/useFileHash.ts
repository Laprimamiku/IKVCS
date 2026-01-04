/**
 * 文件哈希计算 Composable
 * 
 * 职责：计算文件 SHA-256 哈希值，用于秒传检测和断点续传
 */
import { ref } from 'vue'

export function useFileHash() {
  const fileHash = ref<string>('')
  const isCalculating = ref<boolean>(false)

  /**
   * 计算文件哈希（SHA-256）
   * @param file 要计算哈希的文件
   * @returns 文件的 SHA-256 哈希值（十六进制字符串）
   */
  const calculateFileHash = async (file: File): Promise<string> => {
    isCalculating.value = true
    try {
      const buffer = await file.arrayBuffer()
      const hashBuffer = await crypto.subtle.digest('SHA-256', buffer)
      const hashArray = Array.from(new Uint8Array(hashBuffer))
      const hashHex = hashArray
        .map((b) => b.toString(16).padStart(2, '0'))
        .join('')
      fileHash.value = hashHex
      return hashHex
    } catch (error) {
      console.error('计算文件哈希失败:', error)
      throw new Error('计算文件哈希失败')
    } finally {
      isCalculating.value = false
    }
  }

  /**
   * 重置哈希值
   */
  const resetHash = () => {
    fileHash.value = ''
    isCalculating.value = false
  }

  return {
    fileHash,
    isCalculating,
    calculateFileHash,
    resetHash,
  }
}

