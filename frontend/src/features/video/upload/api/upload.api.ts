/**
 * 上传相关 API
 * 
 * 封装视频分片上传相关的 API 请求
 * 
 * 类比 Java：
 *   相当于 UploadService 接口调用
 */
import { request } from "@/shared/utils/request"
import type { ApiResponse } from "@/shared/types/entity"

export interface InitUploadData {
  file_hash: string
  file_name: string
  total_chunks: number
  file_size: number
}

export interface InitUploadResponse {
  is_completed: boolean
  video_id?: number
  uploaded_chunks?: number[]
}

export interface FinishUploadData {
  file_hash: string
  title: string
  description?: string
  category_id: number
  cover_url?: string
}

export interface FinishUploadResponse {
  video_id: number
}

export interface UploadProgressResponse {
  uploaded_chunks: number[]
  total_chunks: number
}

/**
 * 初始化上传
 * 
 * @param data - 上传初始化数据
 * @returns 返回上传会话信息
 * 
 * 需求：3.1, 3.2
 */
export function initUpload(data: InitUploadData) {
  return request.post<InitUploadResponse>('/upload/init', data)
}

/**
 * 上传分片
 * 
 * @param fileHash - 文件哈希
 * @param chunkIndex - 分片索引
 * @param chunkData - 分片数据
 * @returns 返回上传结果
 * 
 * 需求：3.3, 3.4
 */
export function uploadChunk(fileHash: string, chunkIndex: number, chunkData: Blob) {
  const formData = new FormData()
  formData.append('file_hash', fileHash)
  formData.append('chunk_index', chunkIndex.toString())
  formData.append('chunk', chunkData)
  
  return request.post<ApiResponse>('/upload/chunk', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

/**
 * 完成上传
 * 
 * @param data - 完成上传数据
 * @returns 返回视频信息
 * 
 * 需求：3.5, 3.6
 */
export function finishUpload(data: FinishUploadData) {
  return request.post<FinishUploadResponse>('/upload/finish', data)
}

/**
 * 查询上传进度
 * 
 * @param fileHash - 文件哈希
 * @returns 返回上传进度信息
 * 
 * 需求：3.4
 */
export function getUploadProgress(fileHash: string) {
  return request.get<UploadProgressResponse>(`/upload/progress/${fileHash}`)
}

