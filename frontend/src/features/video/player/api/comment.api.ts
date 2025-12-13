import { request } from "@/shared/utils/request";
import type { ApiResponse, PageResult, Comment, CommentCreatePayload } from "@/shared/types/entity";

// 获取评论列表
// ✅ 修正：泛型只传 PageResult<Comment>，不需要再包一层 ApiResponse
export function getComments(videoId: number, params: { page: number; page_size: number; sort_by: 'new' | 'hot' }) {
  return request.get<PageResult<Comment>>(`/videos/${videoId}/comments`, { params });
}

// 获取子评论/回复
// ✅ 修正：同上
export function getReplies(commentId: number, params: { page: number; page_size: number }) {
  return request.get<PageResult<Comment>>(`/comments/${commentId}/replies`, { params });
}

// 发表评论
// ✅ 修正：泛型只传 Comment
export function createComment(videoId: number, data: CommentCreatePayload) {
  return request.post<Comment>(`/videos/${videoId}/comments`, data);
}

// 删除评论
// ✅ 修正：泛型只传 null
export function deleteComment(commentId: number) {
  return request.delete<null>(`/comments/${commentId}`);
}