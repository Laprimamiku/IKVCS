import { request } from '@/shared/utils/request';
import type { User, AiAnalysisResult } from '@/shared/types/entity';

// ==================== 数据类型定义 ====================

export interface StatsOverview {
  total_users: number;
  new_users_today: number;
  active_users_today: number;
  total_videos: number;
  new_videos_today: number;
  total_reports_pending: number;
  total_views: number;
  total_likes: number;
  total_collections: number;
  videos_pending_review: number;
}

export interface ChartData {
  date: string;
  user_count: number;
  video_count: number;
  views?: number;
  likes?: number;
  collections?: number;
}

export interface CategoryStat {
  name: string;
  count: number;
}

export interface TargetSnapshotVideo {
  id: number;
  title: string;
  cover_url?: string;
  video_url?: string;
  uploader?: {
    id: number;
    username: string;
    nickname: string;
    avatar?: string;
  };
  status: number;
  review_status: number;
  created_at?: string;
}

export interface TargetSnapshotComment {
  id: number;
  content: string;
  video_id: number;
  user?: {
    id: number;
    username: string;
    nickname: string;
    avatar?: string;
  };
  created_at?: string;
}

export interface TargetSnapshotDanmaku {
  id: number;
  content: string;
  video_id: number;
  video_time: number;
  user?: {
    id: number;
    username: string;
    nickname: string;
    avatar?: string;
  };
  created_at?: string;
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
  target_snapshot?: TargetSnapshotVideo | TargetSnapshotComment | TargetSnapshotDanmaku;
  admin_target_url?: string;
  public_watch_url?: string;
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
  // 举报相关字段
  is_reported?: boolean; // 是否有待处理的举报
  open_report_count?: number; // 待处理举报数量
  last_reported_at?: string; // 最近举报时间
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
  manageVideos: (page = 1, pageSize = 20, status?: number | null, categoryId?: number | null, keyword?: string) =>
    request.get('/admin/videos/manage', { params: { page, page_size: pageSize, status, category_id: categoryId, keyword } }),
  approveVideo: (id: number) => request.post(`/admin/videos/${id}/approve`),
  rejectVideo: (id: number) => request.post(`/admin/videos/${id}/reject`),
  reReviewVideo: (id: number) => request.post(`/admin/videos/${id}/re-review`), // 重新触发AI初审（帧+字幕）
  reviewFramesOnly: (id: number, force?: boolean) =>
    request.post(`/admin/videos/${id}/review-frames`, null, force ? { params: { force: true } } : undefined), // 仅审核视频帧
  reviewSubtitleOnly: (id: number, force?: boolean) =>
    request.post(`/admin/videos/${id}/review-subtitle`, null, force ? { params: { force: true } } : undefined), // 仅审核字幕
  getOriginalVideoUrl: (id: number) => request.get(`/admin/videos/${id}/original`), // 获取原始视频文件 URL
  getSubtitleContent: (id: number) => request.get(`/admin/videos/${id}/subtitle-content`, { silent: true }), // 获取字幕内容

  // 3. 用户管理
  getUsers: (page = 1, keyword = '') => 
    request.get('/admin/users', { params: { page, keyword } }),
  banUser: (id: number) => request.post(`/admin/users/${id}/ban`),
  unbanUser: (id: number) => request.post(`/admin/users/${id}/unban`),

  // 4. 举报处理
  getReports: (status = 0, page = 1) => 
    request.get('/admin/reports', { params: { status, page } }),
  handleReport: (id: number, action: 'delete_target' | 'ignore' | 'disable' | 'request_review', note?: string) => 
    request.post(`/admin/reports/${id}/handle`, { action, admin_note: note }),
    
  // 5. 分类管理 (可选，根据之前后端实现)
  getCategories: () => request.get('/categories'),
  createCategory: (data: { name: string; description?: string }) => request.post('/admin/categories', data),
  updateCategory: (id: number, data: { name?: string; description?: string }) => request.put(`/admin/categories/${id}`, data),
  deleteCategory: (id: number) => request.delete(`/admin/categories/${id}`),

  // 6. 系统设置
  getSystemSettings: () => request.get('/admin/system/settings'),
  updateSystemSettings: (data: any) => request.put('/admin/system/settings', data),
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
  is_active?: boolean;
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

export interface PromptWorkflowTask {
  id: number;
  name: string;
  prompt_type: string;
  goal?: string;
  metrics?: Record<string, string>;
  dataset_source?: string;
  sample_min?: number;
  is_active?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface PromptWorkflowExperiment {
  id: number;
  task_id?: number;
  prompt_type: string;
  candidate_version_id?: number;
  active_version_id?: number;
  model_source?: string;
  dataset_source?: string;
  sample_limit?: number;
  sample_count?: number;
  status?: string;
  metrics?: Record<string, any>;
  created_at?: string;
}

export interface GovernanceOverview {
  window: { days: number; start_at: string; end_at: string };
  overview: {
    total_interactions: number;
    ai_coverage_rate: number;
    quality_score: number;
    risk_score: number;
    governance_score: number;
    risk_rate: number;
    low_quality_rate: number;
    highlight_rate: number;
    auto_review_saving_rate: number;
    avg_score: number;
  };
  distribution: { score_buckets: Record<string, number> };
  quality: {
    highlight_count: number;
    high_quality_count: number;
    low_quality_count: number;
    avg_score: number;
  };
  risk: { risk_count: number; severe_risk_count: number };
  sources: { distribution: Record<string, number>; coverage_rate: number };
  actions: Array<{ type: string; title: string; detail: string }>;
  ablation: Record<string, boolean>;
  thresholds: Record<string, number | number[]>;
  videos: {
    risk: GovernanceVideoItem[];
    highlight: GovernanceVideoItem[];
  };
  computed_at: string;
}

export interface GovernanceVideoItem {
  video_id: number;
  title: string;
  cover_url?: string;
  created_at?: string;
  status?: number;
  review_status?: number;
  uploader?: {
    id: number;
    username: string;
    nickname: string;
    avatar?: string;
  };
  metrics: {
    total_interactions: number;
    risk_count: number;
    severe_risk_count: number;
    highlight_count: number;
    low_quality_count: number;
    ai_coverage_rate: number;
    risk_rate: number;
    highlight_rate: number;
    governance_score: number;
  };
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
  submitCorrection: (data: {
    content_type: string;
    content: string;
    original_result: AiAnalysisResult;
    corrected_result: AiAnalysisResult;
    correction_reason: string;
    prompt_version_id?: number;
    model_config_snapshot?: Record<string, any>;
    decision_trace_snapshot?: Record<string, any>;
  }) => {
    return request.post('/admin/ai/correct', data);
  },

  // 新增：Shadow测试
  shadowTestPrompt: (data: { candidate_version_id: number; sample_limit: number; model_source?: string; dataset_source?: string; task_id?: number }) => {
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
  },

  // Prompt workflow tasks
  getPromptWorkflowTasks: () => {
    return request.get<{ items: PromptWorkflowTask[]; total: number }>('/admin/ai/prompt-workflow/tasks');
  },
  createPromptWorkflowTask: (data: {
    name: string;
    prompt_type: string;
    goal?: string;
    metrics?: Record<string, string>;
    dataset_source?: string;
    sample_min?: number;
    is_active?: boolean;
  }) => {
    return request.post('/admin/ai/prompt-workflow/tasks', data);
  },
  updatePromptWorkflowTask: (taskId: number, data: {
    name?: string;
    goal?: string;
    metrics?: Record<string, string>;
    dataset_source?: string;
    sample_min?: number;
    is_active?: boolean;
  }) => {
    return request.put(`/admin/ai/prompt-workflow/tasks/${taskId}`, data);
  },

  runPromptWorkflowTest: (data: { candidate_version_id: number; sample_limit?: number; model_source?: string; dataset_source?: string; task_id?: number }) => {
    return request.post('/admin/ai/prompt-workflow/test', data);
  },
  getPromptWorkflowExperiments: (params?: { task_id?: number; prompt_type?: string; limit?: number }) => {
    return request.get<{ items: PromptWorkflowExperiment[]; total: number }>('/admin/ai/prompt-workflow/experiments', { params });
  },
  getPromptWorkflowExperiment: (experimentId: number) => {
    return request.get<PromptWorkflowExperiment>(`/admin/ai/prompt-workflow/experiments/${experimentId}`);
  },

  createPromptDraft: (data: { prompt_type: string; draft_content: string; sample_ids?: number[]; risk_notes?: string[]; expected_impact?: string }) => {
    return request.post('/admin/ai/prompts/create-draft', data);
  },

  // [New] AI治理总览
  getGovernanceOverview: (params?: { days?: number; limit?: number }) => {
    return request.get<GovernanceOverview>('/admin/ai/governance/overview', { params });
  }
};
