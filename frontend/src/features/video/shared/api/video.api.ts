import { request, uploadRequest } from "@/shared/utils/request";
import type { Video, PageResult, VideoQueryParams } from "@/shared/types/entity";
import { processVideoUrls, processVideoList } from "@/shared/utils/apiHelpers";

/**
 * 获取视频列表
 */
export async function getVideoList(params: VideoQueryParams) {
  const response = await request.get<PageResult<Video>>('/videos', { params });
  if (response.success && response.data) {
    response.data.items = processVideoList(response.data.items);
  }
  return response;
}

/**
 * 获取视频详情
 */
export async function getVideoDetail(videoId: number) {
  const response = await request.get<Video>(`/videos/${videoId}`);
  if (response.success && response.data) {
    response.data = processVideoUrls(response.data);
  }
  return response;
}

/**
 * 增加播放量
 */
export function incrementViewCount(videoId: number) {
  return request.post(`/videos/${videoId}/view`);
}

/**
 * 上传封面
 */
export function uploadVideoCover(videoId: number, file: File) {
  const formData = new FormData();
  formData.append('cover', file);
  return uploadRequest.post(`/videos/${videoId}/cover`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
}

/**
 * 上传字幕
 */
export function uploadVideoSubtitle(videoId: number, file: File) {
  const formData = new FormData();
  formData.append('subtitle', file);
  return uploadRequest.post(`/videos/${videoId}/subtitle`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
}

/**
 * 获取我的视频列表 (后台管理用)
 */
export async function getMyVideos(params: { page: number; page_size: number; status?: number }) {
  const response = await request.get<PageResult<Video>>('/videos/my', { params });
  if (response.success && response.data) {
    response.data.items = processVideoList(response.data.items);
  }
  return response;
}

/**
 * 更新视频信息
 */
export function updateVideo(videoId: number, data: { title?: string; description?: string; category_id?: number }) {
  return request.put(`/videos/${videoId}`, data);
}

/**
 * 删除视频
 */
export function deleteVideo(videoId: number) {
  return request.delete(`/videos/${videoId}`);
}

/**
 * 点赞/取消点赞视频
 */
export function toggleVideoLike(videoId: number) {
  return request.post<{ is_liked: boolean; like_count: number }>(`/videos/${videoId}/like`);
}

/**
 * 收藏/取消收藏视频
 * @param videoId - 视频ID
 * @param folderId - 文件夹ID（可选，null 表示未分类，undefined 表示取消收藏）
 */
export function toggleVideoCollect(videoId: number, folderId?: number | null) {
  // 如果 folderId 是 undefined，说明是取消收藏，不传 folder_id
  // 如果 folderId 是 null，说明收藏到未分类
  // 如果 folderId 是数字，说明收藏到指定文件夹
  const data = folderId !== undefined ? { folder_id: folderId } : {};
  return request.post<{ is_collected: boolean; collect_count: number }>(`/videos/${videoId}/collect`, data);
}

/**
 * 获取我的收藏列表
 */
export async function getMyCollections(params: { page: number; page_size: number; folder_id?: number | null }) {
  const response = await request.get<PageResult<Video>>('/users/me/favorites', { params });
  if (response.success && response.data) {
    // 同样处理视频列表格式
    response.data.items = processVideoList(response.data.items);
  }
  return response;
}

/**
 * [New] 获取视频 AI 智能分析报告
 */
export function getAnalysis(videoId: number) {
  return request.get<any>(`/videos/${videoId}/ai-analysis`);
}

/**
 * 获取AI分析明细（弹幕/评论）
 */
export function getAnalysisItems(videoId: number, params: Record<string, any>) {
  return request.get<any>(`/videos/${videoId}/ai-analysis/items`, { params });
}

/**
 * 触发AI分析重算（占位，后台任务需配合）
 */
export function triggerAnalysisRecompute(videoId: number, data?: { scope?: string; limit?: number }) {
  return request.post<any>(`/videos/${videoId}/ai-analysis/recompute`, data);
}

/**
 * 手动触发多智能体复核（仅上传者/管理员）
 */
export function triggerJuryReview(videoId: number, data?: { scope?: string; limit?: number }) {
  return request.post<any>(`/videos/${videoId}/ai-analysis/jury`, data);
}

/**
 * 查询AI分析重算进度
 */
export function getAnalysisProgress(videoId: number) {
  return request.get<any>(`/videos/${videoId}/ai-analysis/progress`);
}

/**
 * 管理端：获取 AI 配置概览
 */
export function getAiConfigOverview() {
  return request.get<any>(`/admin/ai/config`);
}

/**
 * 管理端：获取 AI 埋点计数
 */
export function getAiMetrics(params?: { target_date?: string; metrics?: string[] }) {
  return request.get<any>(`/admin/ai/metrics`, { params });
}

/**
 * 获取视频大纲
 */
export async function getVideoOutline(videoId: number) {
  return request.get<{ outline: any[] }>(`/videos/${videoId}/outline`);
}

/**
 * 生成视频大纲
 */
export function generateVideoOutline(videoId: number, force?: boolean) {
  return request.post<{ outline: any[]; message: string }>(
    `/videos/${videoId}/outline/generate`,
    null,
    force ? { params: { force: true } } : undefined
  );
}

/**
 * 获取大纲生成进度
 */
export function getOutlineProgress(videoId: number) {
  return request.get<{ progress: number; message: string; status: string }>(`/videos/${videoId}/outline/progress`);
}

/**
 * 获取视频摘要
 */
export async function getVideoSummary(videoId: number) {
  return request.get<{ summary_short?: string; summary_detailed?: string }>(`/videos/${videoId}/summary`);
}

/**
 * 生成视频摘要
 */
export function generateVideoSummary(videoId: number) {
  return request.post(`/videos/${videoId}/summary`);
}

/**
 * 完成视频重新上传
 */
export function finishReupload(videoId: number, fileHash: string) {
  const formData = new FormData();
  formData.append('file_hash', fileHash);
  return uploadRequest.post(`/videos/${videoId}/reupload/finish`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
}

/**
 * 获取核心知识点
 */
export async function getVideoKnowledge(videoId: number) {
  return request.get<{ knowledge_points: any }>(`/videos/${videoId}/knowledge`);
}

// ==========================================
// 统一导出对象 (修复 SmartAnalysis.vue 报错)
// ==========================================
export const videoApi = {
  getVideoList,
  getVideoDetail,
  incrementViewCount,
  uploadVideoCover,
  uploadVideoSubtitle,
  getMyVideos,
  updateVideo,
  deleteVideo,
  toggleVideoLike,
  toggleVideoCollect,
  getMyCollections,
  getAnalysis,
  getAnalysisItems,
  triggerAnalysisRecompute,
  triggerJuryReview,
  getAnalysisProgress, // 包含新增的分析接口
  getAiConfigOverview,
  getAiMetrics
};
