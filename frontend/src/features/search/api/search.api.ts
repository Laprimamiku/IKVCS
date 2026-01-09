import { request } from "@/shared/utils/request";
import type { Video, PageResult } from "@/shared/types/entity";

/**
 * 搜索视频参数
 */
export interface SearchVideoParams {
  q?: string;  // 搜索关键词
  category_id?: number;
  status?: number;
  created_from?: string;
  created_to?: string;
  duration_min?: number;
  duration_max?: number;
  uploader_id?: number;
  sort_by?: "created" | "view" | "like";
  order?: "asc" | "desc";
  page?: number;
  page_size?: number;
}

/**
 * 搜索视频响应
 */
export interface SearchVideoResponse {
  items: Video[];
  total: number;
  page: number;
  page_size: number;
  suggestions?: string[];
  highlights?: Record<number, string>;
}

/**
 * 搜索建议响应
 */
export interface SearchSuggestionsResponse {
  suggestions: string[];
  hotwords?: Array<{ keyword: string; count: number }>;
}

/**
 * 搜索视频
 */
export async function searchVideos(params: SearchVideoParams) {
  const response = await request.get<SearchVideoResponse>("/search/videos", { params });
  if (response.success && response.data) {
    // 处理视频列表（URL 处理等）
    const { processVideoList } = await import("@/shared/utils/apiHelpers");
    response.data.items = processVideoList(response.data.items);
  }
  return response;
}

/**
 * 获取搜索建议
 */
export async function getSearchSuggestions(q?: string, limit = 10) {
  return request.get<SearchSuggestionsResponse>("/search/suggestions", {
    params: { q, limit }
  });
}

