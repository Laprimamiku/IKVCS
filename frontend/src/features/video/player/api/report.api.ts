import { request } from "@/shared/utils/request";

export interface ReportCreateData {
  target_type: "VIDEO" | "COMMENT" | "DANMAKU";
  target_id: number;
  reason: string;
  description?: string;
}

/**
 * 提交举报
 * 注意：后端路由注册在 /api/v1，路径是 /reports
 * 所以完整路径是 /api/v1/reports
 */
export function createReport(data: ReportCreateData) {
  return request.post<{ message: string }>("/reports", data);
}
