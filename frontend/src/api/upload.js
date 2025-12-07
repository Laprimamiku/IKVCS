/**
 * 上传相关 API
 * 
 * 封装视频分片上传相关的 API 请求
 * 
 * 类比 Java：
 *   相当于 UploadService 接口调用
 */
import request from '@/utils/request'

/**
 * 初始化上传
 * 
 * @param {Object} data - 上传初始化数据
 * @param {string} data.file_hash - 文件哈希（SHA-256）
 * @param {string} data.file_name - 文件名
 * @param {number} data.total_chunks - 总分片数
 * @param {number} data.file_size - 文件大小（字节）
 * @returns {Promise} 返回上传会话信息
 * 
 * 需求：3.1, 3.2
 */
export function initUpload(data) {
  return request({
    url: '/upload/init',
    method: 'post',
    data
  })
}

/**
 * 上传分片
 * 
 * @param {string} fileHash - 文件哈希
 * @param {number} chunkIndex - 分片索引
 * @param {Blob} chunkData - 分片数据
 * @returns {Promise} 返回上传结果
 * 
 * 需求：3.3, 3.4
 */
export function uploadChunk(fileHash, chunkIndex, chunkData) {
  const formData = new FormData()
  formData.append('file_hash', fileHash)
  formData.append('chunk_index', chunkIndex)
  formData.append('chunk', chunkData)
  
  return request({
    url: '/upload/chunk',
    method: 'post',
    data: formData,
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

/**
 * 完成上传
 * 
 * @param {Object} data - 完成上传数据
 * @param {string} data.file_hash - 文件哈希
 * @param {string} data.title - 视频标题
 * @param {string} data.description - 视频描述
 * @param {number} data.category_id - 分类ID
 * @param {string} data.cover_url - 封面图URL
 * @returns {Promise} 返回视频信息
 * 
 * 需求：3.5, 3.6
 */
export function finishUpload(data) {
  return request({
    url: '/upload/finish',
    method: 'post',
    data
  })
}

/**
 * 查询上传进度
 * 
 * @param {string} fileHash - 文件哈希
 * @returns {Promise} 返回上传进度信息
 * 
 * 需求：3.4
 */
export function getUploadProgress(fileHash) {
  return request({
    url: `/upload/progress/${fileHash}`,
    method: 'get'
  })
}
