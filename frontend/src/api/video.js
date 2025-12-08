/**
 * 视频相关 API
 * 
 * 封装视频列表、搜索、详情等 API 请求
 */
import request from '@/utils/request'

/**
 * 获取视频列表
 * 
 * @param {Object} params - 查询参数
 * @param {number} params.page - 页码（从1开始）
 * @param {number} params.page_size - 每页数量
 * @param {number} params.category_id - 分类ID（可选）
 * @param {string} params.keyword - 搜索关键词（可选）
 * @returns {Promise} 返回视频列表和分页信息
 * 
 * 需求：5.1, 5.2, 5.3
 */
export function getVideoList(params) {
  return request({
    url: '/videos',
    method: 'get',
    params
  })
}

/**
 * 获取视频详情
 * 
 * @param {number} videoId - 视频ID
 * @returns {Promise} 返回视频详细信息
 * 
 * 需求：5.4
 */
export function getVideoDetail(videoId) {
  return request({
    url: `/videos/${videoId}`,
    method: 'get'
  })
}

/**
 * 搜索视频
 * 
 * @param {Object} params - 搜索参数
 * @param {string} params.keyword - 搜索关键词
 * @param {number} params.page - 页码
 * @param {number} params.page_size - 每页数量
 * @param {number} params.category_id - 分类ID（可选）
 * @returns {Promise} 返回搜索结果
 * 
 * 需求：5.3
 */
export function searchVideos(params) {
  return request({
    url: '/videos',
    method: 'get',
    params
  })
}

/**
 * 增加视频播放量
 * 
 * @param {number} videoId - 视频ID
 * @returns {Promise}
 * 
 * 需求：5.5
 */
export function incrementViewCount(videoId) {
  return request({
    url: `/videos/${videoId}/view`,
    method: 'post'
  })
}

/**
 * 上传封面
 * @param {number} videoId
 * @param {File} file
 */
export function uploadVideoCover(videoId, file) {
  const formData = new FormData()
  formData.append('cover', file)

  return request({
    url: `/videos/${videoId}/cover`,
    method: 'post',
    data: formData,
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

/**
 * 上传字幕
 * @param {number} videoId
 * @param {File} file
 */
export function uploadVideoSubtitle(videoId, file) {
  const formData = new FormData()
  formData.append('subtitle', file)

  return request({
    url: `/videos/${videoId}/subtitle`,
    method: 'post',
    data: formData,
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}
