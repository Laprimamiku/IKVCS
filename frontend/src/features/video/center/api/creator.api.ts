import { request } from "@/shared/utils/request";

export interface CreatorStatsResponse {
  totals: {
    total_videos: number;
    total_views: number;
    total_likes: number;
    total_comments: number;
    total_danmakus: number;
    total_collections: number;
  };
  daily: {
    dates: string[];
    views: number[];
    comments: number[];
    danmakus: number[];
  };
  top_videos: Array<{
    id: number;
    title: string;
    view_count: number;
    like_count: number;
    collect_count: number;
    comment_count: number;
    danmaku_count: number;
  }>;
}

export function getCreatorStats(days: number) {
  return request.get<CreatorStatsResponse>("/users/me/creator/stats", { params: { days } });
}
