import { request } from "@/shared/utils/request"
import type { Danmaku, DanmakuSendPayload } from "@/shared/types/entity"

/**
 * 获取视频历史弹幕
 */
export async function getDanmakus(videoId: number) {
  return request.get<Danmaku[]>(`/videos/${videoId}/danmakus`)
}

/**
 * 发送弹幕
 */
export async function sendDanmaku(videoId: number, payload: DanmakuSendPayload) {
  return request.post<Danmaku>(`/videos/${videoId}/danmakus`, payload)
}

/**
 * 点赞/取消点赞弹幕
 */
export function toggleDanmakuLike(videoId: number, danmakuId: number) {
  return request.post<{ is_liked: boolean; like_count: number }>(`/videos/${videoId}/danmakus/${danmakuId}/like`);
}

