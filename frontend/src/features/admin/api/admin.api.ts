import { request } from '@/shared/utils/request';
import type { User } from '@/shared/types/entity';

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
  duration: number;
  description: string;
  created_at: string;
  uploader: User;
  category: { id: number; name: string };
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
  approveVideo: (id: number) => request.post(`/admin/videos/${id}/approve`),
  rejectVideo: (id: number) => request.post(`/admin/videos/${id}/reject`),

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
  createCategory: (data: any) => request.post('/admin/categories', data),
  updateCategory: (id: number, data: any) => request.put(`/admin/categories/${id}`, data),
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

export interface ErrorPatternAnalysis {
  error_patterns: any;
  suggestions: string; // Markdown
  sample_count: number;
  analysis_date: string;
}

export interface CorrectionRecord {
  id: number;
  content: string;
  original_result: any;
  corrected_result: any;
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
  }
};
