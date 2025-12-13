import { request } from "@/shared/utils/request";
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
  return request.post(`/videos/${videoId}/cover`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
}

/**
 * 上传字幕
 */
export function uploadVideoSubtitle(videoId: number, file: File) {
  const formData = new FormData();
  formData.append('subtitle', file);
  return request.post(`/videos/${videoId}/subtitle`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
}

/**
 * 获取我的视频列表
 */
import type { MyVideosQueryParams } from "@/shared/types/entity";

export async function getMyVideos(params: MyVideosQueryParams) {
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
export function deleteVideo(videoId: number, hardDelete: boolean = true) {
  return request.delete(`/videos/${videoId}`, { params: { hard_delete: hardDelete } });
}

/**
 * 点赞/取消点赞视频
 */
export function toggleVideoLike(videoId: number) {
  return request.post<{ is_liked: boolean; like_count: number }>(`/videos/${videoId}/like`);
}

/**
 * 收藏/取消收藏视频
 */
export function toggleVideoCollect(videoId: number) {
  return request.post<{ is_collected: boolean; collect_count: number }>(`/videos/${videoId}/collect`);
}

/**
 * 获取我的收藏列表
 */
export async function getMyCollections(params: { page: number; page_size: number }) {
  const response = await request.get<PageResult<Video>>('/users/me/favorites', { params });
  if (response.success && response.data) {
    // 假设 apiHelpers 里的处理函数也适用于收藏列表
    // response.data.items = processVideoList(response.data.items);
    // 这里简单处理封面图路径
    response.data.items.forEach(v => {
      if (v.cover_url && !v.cover_url.startsWith('http')) {
        v.cover_url = import.meta.env.VITE_API_BASE_URL + v.cover_url;
      }
    });
  }
  return response;
}