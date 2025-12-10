// src/types/entity.ts

// 通用 API 响应结构
export interface ApiResponse<T = unknown> {
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
  subtitle_url?: string;
  duration: number;
  view_count: number;
  like_count: number;
  collect_count?: number;
  danmaku_count?: number; // 后端可能需要补这个字段，前端暂用0
  status?: number; // 0: 转码中, 1: 审核中, 2: 已发布, 3: 已拒绝, 4: 已删除
  category_id?: number;
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

// 推荐视频项（用于推荐列表）
export interface RecommendVideo {
  id: number;
  title: string;
  cover: string;
  uploader: string;
  views: number;
}

// 用户完整信息（包含时间字段）
export interface UserInfo {
  id: number;
  username: string;
  nickname: string;
  avatar?: string;
  intro?: string;
  role: string;
  created_at: string;
  last_login_time?: string;
}

// 视频查询参数
export interface VideoQueryParams {
  page: number;
  page_size: number;
  category_id?: number | null;
  keyword?: string;
}

// 我的视频查询参数
export interface MyVideosQueryParams {
  page: number;
  page_size: number;
  status?: number | null;
}

// 视频更新数据
export interface VideoUpdateData {
  title?: string;
  description?: string;
  category_id?: number;
}