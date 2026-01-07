import { request } from '@/shared/utils/request';
import type { User, AiAnalysisResult } from '@/shared/types/entity';

// ==================== 数据类型定义 ====================

export interface StatsOverview {
  total_users: number;
  new_users_today: number;
  total_videos: number;
  new_videos_today: number;
  total_reports_pending: number;
}

export interface ChartData {
  date: string;
  user_count: number;
  video_count: number;
}

export interface CategoryStat {
  name: string;
  count: number;
}

export interface ReportItem {
  id: number;
  target_type: 'VIDEO' | 'COMMENT' | 'DANMAKU';
  target_id: number;
  reason: string;
  description?: string;
  status: number;
  created_at: string;
  reporter: User;
}

export interface AuditVideoItem {
  id: number;
  title: string;
  cover_url: string;
  video_url: string;
  subtitle_url?: string; // 字幕文件 URL
  duration: number;
  description: string;
  created_at: string;
  uploader: User;
  category: { id: number; name: string };
  status?: number; // 视频状态：0=转码中, 1=审核中, 2=已发布, 3=已拒绝, 4=已删除
  review_score?: number; // 综合审核评分（0-100）
  review_status?: number; // 审核状态：0=待审核，1=通过，2=拒绝
  review_report?: {
    timestamp?: string;
    frame_review?: any;
    subtitle_review?: any;
    final_score?: number;
    final_status?: number;
    error?: string;
    message?: string;
  }; // 审核报告详情
}

// ==================== API 方法 ====================

export const adminApi = {
  // 1. 数据统计
  getOverview: () => request.get<StatsOverview>('/admin/statistics/overview'),
  getTrends: (days = 7) => request.get<ChartData[]>('/admin/statistics/trends', { params: { days } }),
  getCategoryStats: () => request.get<CategoryStat[]>('/admin/statistics/categories'),

  // 2. 视频审核
  getPendingVideos: (page = 1, pageSize = 20) => 
    request.get('/admin/videos/pending', { params: { page, page_size: pageSize } }),
  manageVideos: (page = 1, pageSize = 20, status?: number | null, keyword?: string) =>
    request.get('/admin/videos/manage', { params: { page, page_size: pageSize, status, keyword } }),
  approveVideo: (id: number) => request.post(`/admin/videos/${id}/approve`),
  rejectVideo: (id: number) => request.post(`/admin/videos/${id}/reject`),
  reReviewVideo: (id: number) => request.post(`/admin/videos/${id}/re-review`), // 重新触发AI初审（帧+字幕）
  reviewFramesOnly: (id: number) => request.post(`/admin/videos/${id}/review-frames`), // 仅审核视频帧
  reviewSubtitleOnly: (id: number) => request.post(`/admin/videos/${id}/review-subtitle`), // 仅审核字幕
  getOriginalVideoUrl: (id: number) => request.get(`/admin/videos/${id}/original`), // 获取原始视频文件 URL
  getSubtitleContent: (id: number) => request.get(`/admin/videos/${id}/subtitle-content`), // 获取字幕内容

  // 3. 用户管理
  getUsers: (page = 1, keyword = '') => 
    request.get('/admin/users', { params: { page, keyword } }),
  banUser: (id: number) => request.post(`/admin/users/${id}/ban`),
  unbanUser: (id: number) => request.post(`/admin/users/${id}/unban`),

  // 4. 举报处理
  getReports: (status = 0, page = 1) => 
    request.get('/admin/reports', { params: { status, page } }),
  handleReport: (id: number, action: 'delete_target' | 'ignore', note?: string) => 
    request.post(`/admin/reports/${id}/handle`, { action, admin_note: note }),
    
  // 5. 分类管理 (可选，根据之前后端实现)
  getCategories: () => request.get('/categories'),
  createCategory: (data: { name: string; description?: string }) => request.post('/admin/categories', data),
  updateCategory: (id: number, data: { name?: string; description?: string }) => request.put(`/admin/categories/${id}`, data),
  deleteCategory: (id: number) => request.delete(`/admin/categories/${id}`),
};

// ==========================================
// AI 治理相关接口 (新增)
// ==========================================

export interface PromptVersion {
  id: number;
  prompt_type: string;
  prompt_content: string;
  update_reason: string;
  updated_by: number;
  created_at: string;
}

export interface ErrorPattern {
  pattern: string;
  frequency: number;
  examples: string[];
}

export interface ErrorPatternAnalysis {
  error_patterns: ErrorPattern[];
  suggestions: string; // Markdown
  sample_count: number;
  analysis_date: string;
}

export interface CorrectionRecord {
  id: number;
  content: string;
  original_result: AiAnalysisResult;
  corrected_result: AiAnalysisResult;
  correction_reason: string;
  created_at: string;
}

export const adminAiApi = {
  // 获取 Prompt 版本历史
  getPromptVersions: (params: { prompt_type?: string; limit?: number }) => {
    return request.get<{ items: PromptVersion[]; total: number }>('/admin/ai/prompt-versions', { params });
  },

  // 触发自我纠错分析
  analyzeErrors: (data: { days: number; content_type?: string }) => {
    return request.post<ErrorPatternAnalysis>('/admin/ai/self-correction/analyze', data);
  },

  // 应用 Prompt 更新
  updatePrompt: (data: { prompt_type: string; new_prompt: string; update_reason: string }) => {
    return request.post('/admin/ai/self-correction/update-prompt', data);
  },

  // 获取人工修正记录
  getCorrections: (params: { page: number; page_size: number; content_type?: string }) => {
    return request.get<{ items: CorrectionRecord[]; total: number }>('/admin/ai/corrections', { params });
  },

  // 提交人工修正
  submitCorrection: (data: { type: string; content: string; original_score: number; corrected_score: number; reason: string }) => {
    return request.post('/admin/ai/correct', data);
  },

  // 新增：Shadow测试
  shadowTestPrompt: (data: { candidate_version_id: number; sample_limit: number }) => {
    return request.post('/admin/ai/prompts/shadow-test', data);
  },

  // 新增：获取AI指标
  getAiMetrics: (targetDate?: string) => {
    return request.get('/admin/ai/metrics', { params: { target_date: targetDate } });
  },

  // 新增：获取AI配置概览
  getAiConfig: () => {
    return request.get('/admin/ai/config');
  },

  // 新增：发布Prompt版本
  publishPrompt: (data: { version_id: number }) => {
    return request.post('/admin/ai/prompts/publish', data);
  },

  // 新增：回滚Prompt版本
  rollbackPrompt: (data: { version_id: number }) => {
    return request.post('/admin/ai/prompts/rollback', data);
  }
};
