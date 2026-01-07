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

// [Fix] 添加 User 类型别名，解决 admin.api.ts 的引用错误
export type User = UserInfo;

// [New] 多智能体专家结果接口
export interface ExpertResult {
  score: number;
  category: string;
  label: string;
  reason: string;
  is_highlight: boolean;
  is_inappropriate: boolean;
  confidence?: number;
}

// [New] AI 分析结果接口 (对应后端 AiAnalysisResult)
export interface AiAnalysisResult {
  score: number;               // 0-100 score
  category: string;            // Content category
  label: string;               // Label
  reason: string;              // Analysis reasoning
  source: 'local' | 'cloud';   // Inference source (based on LocalModelService)
  confidence: number;          // Confidence level (0.0-1.0)
  is_highlight: boolean;       // Whether to highlight
  is_inappropriate: boolean;   // Whether it is inappropriate
  expert_results?: ExpertResult[];      // Raw opinions from the Multi-Agent Jury
  conflict_resolved?: boolean; // Whether a Judge Agent was triggered
}

// 视频大纲条目
export interface VideoOutlineEntry {
  title: string;
  start_time: number; // 开始时间（秒）
  end_time?: number; // 结束时间（秒）
  description?: string;
  key_points?: string[]; // 关键知识点/内容点列表
  thumbnail?: string; // 缩略图URL（可选）
}

// 核心知识点
export interface KnowledgePoints {
  concepts?: string[]; // 概念定义
  steps?: string[]; // 操作步骤
  data?: string[]; // 关键数据/统计
  opinions?: string[]; // 重要观点/结论
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
  comment_count?: number;
  collect_count?: number;
  danmaku_count?: number; // 后端可能需要补这个字段，前端暂用0
  
  // [New] 新增互动状态字段
  is_liked?: boolean;
  is_collected?: boolean;
  
  // [New] AI 分析数据
  ai_analysis_result?: AiAnalysisResult;

  // [New] AI 智能分析模块新增字段
  outline?: VideoOutlineEntry[] | string; // 视频大纲（JSON字符串或对象数组）
  summary_short?: string; // 简短摘要（50-100字）
  summary_detailed?: string; // 详细摘要（200-300字）
  knowledge_points?: KnowledgePoints; // 核心知识点

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
  is_deleted?: boolean;
  // [New] 新增点赞相关字段
  like_count?: number;   // 点赞数
  is_liked?: boolean;    // 当前用户是否已点赞
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
  id?: number; // 弹幕ID，用于举报
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
  reply_to_user_id?: number | null;
  content: string;
  like_count: number;
  is_deleted?: boolean;
  created_at: string;

  // [New] 新增互动状态
  is_liked?: boolean;
  
  // 关联用户
  user: UserBrief;
  reply_to_user?: UserBrief; // 回复目标用户（用于@功能）
  
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
  reply_to_user_id?: number | null; // 回复目标用户ID（用于@功能）
}
