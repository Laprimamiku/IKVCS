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

