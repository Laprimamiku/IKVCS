/**
 * 通用分页 Composable
 * 提取分页相关的通用逻辑
 */
import { ref, computed } from 'vue'

export interface UsePaginationOptions {
  initialPage?: number
  initialPageSize?: number
  total?: number
}

export function usePagination(options: UsePaginationOptions = {}) {
  const {
    initialPage = 1,
    initialPageSize = 20,
    total: initialTotal = 0
  } = options

  const currentPage = ref(initialPage)
  const pageSize = ref(initialPageSize)
  const total = ref(initialTotal)

  // 计算属性
  const totalPages = computed(() => {
    return Math.ceil(total.value / pageSize.value)
  })

  const hasMore = computed(() => {
    return currentPage.value < totalPages.value
  })

  const isFirstPage = computed(() => {
    return currentPage.value === 1
  })

  const isLastPage = computed(() => {
    return currentPage.value >= totalPages.value
  })

  // 方法
  const setPage = (page: number) => {
    if (page >= 1 && page <= totalPages.value) {
      currentPage.value = page
    }
  }

  const nextPage = () => {
    if (hasMore.value) {
      currentPage.value++
    }
  }

  const prevPage = () => {
    if (!isFirstPage.value) {
      currentPage.value--
    }
  }

  const setPageSize = (size: number) => {
    if (size > 0) {
      pageSize.value = size
      // 重置到第一页
      currentPage.value = 1
    }
  }

  const setTotal = (newTotal: number) => {
    total.value = newTotal
  }

  const reset = () => {
    currentPage.value = initialPage
    pageSize.value = initialPageSize
    total.value = initialTotal
  }

  return {
    // 状态
    currentPage,
    pageSize,
    total,
    
    // 计算属性
    totalPages,
    hasMore,
    isFirstPage,
    isLastPage,
    
    // 方法
    setPage,
    nextPage,
    prevPage,
    setPageSize,
    setTotal,
    reset
  }
}




















