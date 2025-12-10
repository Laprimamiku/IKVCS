// src/types/entity.ts

// 通用 API 响应结构
export interface ApiResponse<T = any> {
  success: boolean;
  message?: string;
  data: T;
}

// 分页响应结构
export interface PageResult<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// 用户简要信息
export interface UserBrief {
  id: number;
  username: string;
  nickname: string;
  avatar?: string;
}

// 视频信息
export interface Video {
  id: number;
  title: string;
  description?: string;
  cover_url: string;
  video_url?: string;
  duration: number;
  view_count: number;
  like_count: number;
  danmaku_count?: number; // 后端可能需要补这个字段，前端暂用0
  uploader: UserBrief;
  category?: {
    id: number;
    name: string;
  };
  created_at: string;
}

// 分类
export interface Category {
  id: number;
  name: string;
  description?: string;
}