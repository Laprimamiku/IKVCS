/**
 * API 辅助函数
 * 统一处理 API 响应中的文件 URL
 */
import { resolveFileUrl } from './urlHelpers';
import type { Video, UserInfo, UserBrief } from '@/types/entity';

/**
 * 处理视频对象中的文件 URL
 */
export function processVideoUrls(video: Video): Video {
  return {
    ...video,
    cover_url: video.cover_url ? resolveFileUrl(video.cover_url) : '',
    video_url: video.video_url ? resolveFileUrl(video.video_url) : undefined,
    subtitle_url: video.subtitle_url ? resolveFileUrl(video.subtitle_url) : undefined,
  };
}

/**
 * 处理视频列表中的文件 URL
 */
export function processVideoList(videos: Video[]): Video[] {
  return videos.map(processVideoUrls);
}

/**
 * 处理用户信息中的头像 URL
 */
export function processUserInfo(user: UserInfo | UserBrief): UserInfo | UserBrief {
  return {
    ...user,
    avatar: user.avatar ? resolveFileUrl(user.avatar) : undefined,
  };
}

/**
 * 处理用户列表中的头像 URL
 */
export function processUserList<T extends UserInfo | UserBrief>(users: T[]): T[] {
  return users.map(processUserInfo) as T[];
}

