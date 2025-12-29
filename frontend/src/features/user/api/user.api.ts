/**
 * 用户相关 API
 * 
 * 封装用户信息管理相关的 API 请求
 */
import { request } from "@/shared/utils/request"
import type { ApiResponse, UserInfo } from "@/shared/types/entity"
import { processUserInfo } from "@/shared/utils/apiHelpers"

// 兼容旧代码：User 类型等同于 UserInfo
export type User = UserInfo

export interface UpdateUserInfoData {
  nickname?: string
  intro?: string
}

/**
 * 获取当前用户信息
 * 
 * @returns 返回用户信息
 */
export async function getCurrentUser() {
  const response = await request.get<UserInfo>('/users/me')
  if (response.success && response.data) {
    response.data = processUserInfo(response.data) as UserInfo
  }
  return response
}

/**
 * 更新当前用户信息
 * 
 * @param data - 更新数据
 * @returns 返回更新后的用户信息
 */
export async function updateUserInfo(data: UpdateUserInfoData) {
  const response = await request.put<UserInfo>('/users/me', data)
  if (response.success && response.data) {
    response.data = processUserInfo(response.data) as UserInfo
  }
  return response
}

/**
 * 上传用户头像
 * 
 * @param file - 头像文件
 * @returns 返回头像 URL
 */
export function uploadAvatar(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  
  return request.post<ApiResponse<{ avatar_url: string }>>('/users/me/avatar', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

/**
 * 获取指定用户信息（他人主页）
 * 
 * @param userId - 用户 ID
 * @returns 返回用户公开信息
 */
export async function getUserById(userId: number) {
  const response = await request.get<UserInfo>(`/users/${userId}`)
  if (response.success && response.data) {
    response.data = processUserInfo(response.data) as UserInfo
  }
  return response
}

/**
 * 获取观看历史记录（最近3个）
 * 
 * @returns 返回观看历史列表
 */
export interface WatchHistoryItem {
  id: number;
  video_id: number;
  watched_at: string;
  video: {
    id: number;
    title: string;
    cover_url: string;
    duration: number;
    view_count: number;
    like_count: number;
    uploader: {
      id: number;
      nickname: string;
      avatar?: string;
    };
  };
}

export async function getWatchHistory() {
  return request.get<ApiResponse<{ items: WatchHistoryItem[]; total: number }>>('/users/me/watch-history')
}

