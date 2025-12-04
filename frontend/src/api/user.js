/**
 * 用户相关 API
 * 
 * 封装用户信息管理相关的 API 请求
 */
import request from '@/utils/request'

/**
 * 获取当前用户信息
 * 
 * @returns {Promise} 返回用户信息
 */
export function getCurrentUser() {
  return request({
    url: '/users/me',
    method: 'get'
  })
}

/**
 * 更新当前用户信息
 * 
 * @param {Object} data - 更新数据
 * @param {string} data.nickname - 昵称
 * @param {string} data.intro - 简介
 * @returns {Promise} 返回更新后的用户信息
 */
export function updateUserInfo(data) {
  return request({
    url: '/users/me',
    method: 'put',
    data
  })
}

/**
 * 上传用户头像
 * 
 * @param {File} file - 头像文件
 * @returns {Promise} 返回头像 URL
 */
export function uploadAvatar(file) {
  const formData = new FormData()
  formData.append('file', file)
  
  return request({
    url: '/users/me/avatar',
    method: 'post',
    data: formData,
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

/**
 * 获取指定用户信息（他人主页）
 * 
 * @param {number} userId - 用户 ID
 * @returns {Promise} 返回用户公开信息
 */
export function getUserById(userId) {
  return request({
    url: `/users/${userId}`,
    method: 'get'
  })
}
