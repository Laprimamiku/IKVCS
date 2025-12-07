/**
 * 分类相关 API
 * 
 * 封装视频分类相关的 API 请求
 */
import request from '@/utils/request'

/**
 * 获取所有分类
 * 
 * @returns {Promise} 返回分类列表
 * 
 * 需求：6.1
 */
export function getCategories() {
  return request({
    url: '/categories',
    method: 'get'
  })
}

/**
 * 创建分类（管理员）
 * 
 * @param {Object} data - 分类数据
 * @param {string} data.name - 分类名称
 * @param {string} data.description - 分类描述
 * @returns {Promise} 返回创建的分类
 * 
 * 需求：6.2
 */
export function createCategory(data) {
  return request({
    url: '/categories/admin',
    method: 'post',
    data
  })
}
