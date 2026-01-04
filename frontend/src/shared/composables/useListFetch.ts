/**
 * 通用列表获取组合式函数
 * 支持分页、加载状态、自动处理 PageResult<T> 泛型
 */
import { ref, type Ref } from "vue";
import { ElMessage } from "element-plus";
import type { PageResult, ApiResponse } from "@/shared/types/entity";

export interface UseListFetchOptions<T> {
  /** 获取数据的异步函数 */
  fetchFn: (params: any) => Promise<ApiResponse<PageResult<T>>>;
  /** 初始页码 */
  initialPage?: number;
  /** 初始每页数量 */
  initialPageSize?: number;
  /** 数据转换函数（可选，用于将后端数据转换为前端需要的格式） */
  transformFn?: (item: T) => any;
  /** 是否自动加载第一页 */
  autoLoad?: boolean;
  /** 静默模式（不显示错误提示） */
  silent?: boolean;
}

export interface UseListFetchReturn<T> {
  /** 数据列表 */
  items: Ref<T[]>;
  /** 加载状态 */
  loading: Ref<boolean>;
  /** 是否还有更多数据 */
  hasMore: Ref<boolean>;
  /** 当前页码 */
  currentPage: Ref<number>;
  /** 每页数量 */
  pageSize: Ref<number>;
  /** 总数 */
  total: Ref<number>;
  /** 总页数 */
  totalPages: Ref<number>;
  /** 加载数据（替换现有数据） */
  loadData: (params?: Record<string, any>, append?: boolean) => Promise<void>;
  /** 加载更多（追加数据） */
  loadMore: () => Promise<void>;
  /** 刷新数据 */
  refresh: () => Promise<void>;
  /** 重置状态 */
  reset: () => void;
}

/**
 * 通用列表获取组合式函数
 * 
 * @example
 * ```ts
 * const { items, loading, loadData } = useListFetch({
 *   fetchFn: (params) => getVideoList(params),
 *   transformFn: (video) => ({
 *     id: video.id,
 *     title: video.title,
 *     // ... 其他字段转换
 *   }),
 *   autoLoad: true
 * });
 * ```
 */
export function useListFetch<T = any>(
  options: UseListFetchOptions<T>
): UseListFetchReturn<T> {
  const {
    fetchFn,
    initialPage = 1,
    initialPageSize = 20,
    transformFn,
    autoLoad = false,
    silent = false,
  } = options;

  // 状态
  const items: Ref<T[]> = ref([]);
  const loading: Ref<boolean> = ref(false);
  const hasMore: Ref<boolean> = ref(true);
  const currentPage: Ref<number> = ref(initialPage);
  const pageSize: Ref<number> = ref(initialPageSize);
  const total: Ref<number> = ref(0);
  const totalPages: Ref<number> = ref(0);

  /**
   * 加载数据
   * @param params 额外的查询参数
   * @param append 是否追加数据（用于加载更多）
   */
  const loadData = async (
    params: Record<string, any> = {},
    append: boolean = false
  ): Promise<void> => {
    if (loading.value) return;

    loading.value = true;

    try {
      const requestParams = {
        page: currentPage.value,
        page_size: pageSize.value,
        ...params,
      };

      const response = await fetchFn(requestParams);

      if (response.success) {
        const data = response.data as PageResult<T>;
        
        // 转换数据（如果提供了转换函数）
        let newItems: T[] = (data.items || []) as T[];
        if (transformFn) {
          newItems = newItems.map(transformFn) as T[];
        }

        if (append) {
          // 追加模式：追加到现有数据
          items.value.push(...newItems);
        } else {
          // 替换模式：替换现有数据
          items.value = newItems;
        }

        // 更新分页信息
        total.value = data.total || 0;
        totalPages.value = data.total_pages || 0;
        hasMore.value = currentPage.value < totalPages.value;
      } else {
        if (!silent) {
          ElMessage.error(response.message || "加载数据失败");
        }
      }
    } catch (error) {
      console.error("加载数据失败:", error);
      if (!silent) {
        ElMessage.error("加载数据失败");
      }
    } finally {
      loading.value = false;
    }
  };

  /**
   * 加载更多数据
   */
  const loadMore = async (): Promise<void> => {
    if (!hasMore.value || loading.value) return;
    currentPage.value++;
    await loadData({}, true);
  };

  /**
   * 刷新数据（重置到第一页并重新加载）
   */
  const refresh = async (): Promise<void> => {
    currentPage.value = initialPage;
    items.value = [];
    hasMore.value = true;
    await loadData();
  };

  /**
   * 重置状态
   */
  const reset = (): void => {
    items.value = [];
    loading.value = false;
    hasMore.value = true;
    currentPage.value = initialPage;
    pageSize.value = initialPageSize;
    total.value = 0;
    totalPages.value = 0;
  };

  // 自动加载第一页
  if (autoLoad) {
    loadData();
  }

  return {
    items,
    loading,
    hasMore,
    currentPage,
    pageSize,
    total,
    totalPages,
    loadData,
    loadMore,
    refresh,
    reset,
  };
}

