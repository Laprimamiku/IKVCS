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
  role?: string;
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

// 视频详情响应（当前等同于 Video，可在需要时扩展）
export type VideoDetailResponse = Video;

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

// 弹幕
export interface Danmaku {
  id: number;
  video_id: number;
  user_id: number;
  content: string;
  video_time: number;
  color: string;
  created_at: string;
  is_me?: boolean;
  // [New] 新增 AI 分析字段
  ai_score?: number;     // AI 评分 (0-100)
  ai_category?: string;  // AI 分类
  is_highlight?: boolean;// 是否为优质/高亮弹幕
}

export interface DanmakuDisplayItem {
  key: string;
  text: string;
  color: string;
  lane: number;
  initialOffset?: number;
  // [New] 用于展示层的字段
  ai_score?: number;
  is_highlight?: boolean;
}

export interface DanmakuSendPayload {
  content: string;
  video_time: number;
  color: string;
}

export interface DanmakuDisplayItem {
  key: string;
  text: string;
  color: string;
  lane: number;
  // [New]: 记录这条弹幕已经展示了多久（毫秒），用于回退时计算位置
  initialOffset?: number; 
}

// [新增] 评论接口
export interface Comment {
  id: number;
  video_id: number;
  user_id: number;
  parent_id: number | null;
  content: string;
  like_count: number;
  created_at: string;
  
  // 关联用户
  user: UserBrief;
  
  // AI 分析字段
  ai_score?: number;
  ai_label?: string;
  
  // 回复相关
  reply_count: number;
  replies: Comment[]; // 嵌套回复
}

// [新增] 评论创建参数
export interface CommentCreatePayload {
  content: string;
  parent_id?: number | null;
}