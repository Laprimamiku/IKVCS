/**
 * 推荐 API
 */
import request from "@/shared/utils/request";
import type { Video, PageResult } from "@/shared/types/entity";

export interface GetRecommendationsParams {
  scene?: "home" | "detail" | "category";
  category_id?: number | null;
  limit?: number;
}

/**
 * 获取推荐视频列表
 */
export async function getRecommendations(
  params: GetRecommendationsParams = {}
): Promise<{ success: boolean; data: PageResult<Video> }> {
  const { scene = "home", category_id, limit = 20 } = params;
  
  const queryParams: Record<string, any> = {
    scene,
    limit,
  };
  
  if (category_id !== undefined && category_id !== null) {
    queryParams.category_id = category_id;
  }
  
  return request.get("/recommendations/videos", {
    params: queryParams,
  });
}

