import { request } from "@/shared/utils/request";
import type { PageResult, Comment, Danmaku } from "@/shared/types/entity";

export function getManageComments(
  videoId: number,
  params: { page: number; page_size: number; sort_by: "new" | "hot" }
) {
  return request.get<PageResult<Comment>>(`/videos/${videoId}/comments/manage`, { params });
}

export function restoreComment(commentId: number) {
  return request.post(`/comments/${commentId}/restore`);
}

export function getManageDanmakus(videoId: number) {
  return request.get<Danmaku[]>(`/videos/${videoId}/danmakus/manage`);
}

export function deleteDanmaku(videoId: number, danmakuId: number) {
  return request.delete(`/videos/${videoId}/danmakus/${danmakuId}`);
}

export function restoreDanmaku(videoId: number, danmakuId: number) {
  return request.post(`/videos/${videoId}/danmakus/${danmakuId}/restore`);
}
