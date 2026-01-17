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
 * @returns 返回用户公开信息和统计数据
 */
export interface UserProfileData {
  user: UserInfo;
  following_count: number;
  followers_count: number;
  is_following: boolean;
}

export async function getUserById(userId: number) {
  const response = await request.get<ApiResponse<UserProfileData>>(`/users/${userId}`)
  if (response.success && response.data) {
    response.data.user = processUserInfo(response.data.user) as UserInfo
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

export async function getWatchHistory(params?: { page?: number; page_size?: number }) {
  return request.get<ApiResponse<{ items: WatchHistoryItem[]; total: number; page: number; page_size: number }>>('/users/me/watch-history', { params })
}

/**
 * 删除观看历史记录
 * 
 * @param watchHistoryId - 观看历史记录ID
 * @returns 返回删除结果
 */
export async function deleteWatchHistory(watchHistoryId: number) {
  return request.delete<ApiResponse>(`/users/me/watch-history/${watchHistoryId}`)
}

/**
 * 获取用户统计数据
 * 
 * @returns 返回用户统计数据（关注、粉丝、获赞）
 */
export interface UserStats {
  following_count: number
  followers_count: number
  total_likes: number
}

export async function getUserStats() {
  return request.get<ApiResponse<UserStats>>('/users/me/stats')
}

/**
 * 收藏文件夹相关 API
 */
export interface CollectionFolder {
  id: number;
  name: string;
  description?: string;
  count: number;
  created_at: string;
}

export interface CollectionFoldersResponse {
  folders: CollectionFolder[];
  uncategorized_count: number;
}

/**
 * 获取收藏文件夹列表
 */
export async function getCollectionFolders() {
  return request.get<ApiResponse<CollectionFoldersResponse>>('/users/me/favorites/folders')
}

/**
 * 创建收藏文件夹
 */
export async function createCollectionFolder(name: string, description?: string) {
  return request.post<ApiResponse<CollectionFolder>>('/users/me/favorites/folders', {
    name,
    description
  })
}

/**
 * 关注相关 API
 */
export interface FollowUser {
  id: number;
  nickname: string;
  username: string;
  avatar?: string;
  followed_at: string;
}

export interface FollowersResponse {
  following: FollowUser[];
  followers: FollowUser[];
}

/**
 * 获取关注和粉丝列表
 */
export async function getFollowers() {
  return request.get<ApiResponse<FollowersResponse>>('/users/me/followers')
}

/**
 * 关注用户
 */
export async function followUser(userId: number) {
  return request.post<ApiResponse>(`/users/${userId}/follow`)
}

/**
 * 取消关注用户
 */
export async function unfollowUser(userId: number) {
  return request.delete<ApiResponse>(`/users/${userId}/follow`)
}

/**
 * 移除粉丝（被关注者取消对方的关注）
 */
export async function removeFollower(userId: number) {
  return request.delete<ApiResponse>(`/users/${userId}/follower`)
}

