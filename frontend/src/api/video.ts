import { request } from '@/utils/request';
import type { Video, PageResult } from '@/types/entity';

export interface VideoQueryParams {
  page: number;
  page_size: number;
  category_id?: number | null;
  keyword?: string;
}

/**
 * 获取视频列表
 */
export function getVideoList(params: VideoQueryParams) {
  return request.get<PageResult<Video>>('/videos', { params });
}

/**
 * 获取视频详情
 */
export function getVideoDetail(videoId: number) {
  return request.get<Video>(`/videos/${videoId}`);
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