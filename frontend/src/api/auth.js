/**
 * 认证相关 API
 * 
 * 这个文件封装了所有认证相关的 API 请求
 * 相当于 Java 的 Service 接口调用
 */
import request from '@/utils/request'
import { getCurrentUser as getUserInfo } from './user'

/**
 * 用户注册
 * 
 * @param {Object} data - 注册数据
 * @param {string} data.username - 用户名
 * @param {string} data.password - 密码
 * @param {string} data.nickname - 昵称
 * @returns {Promise} 返回用户信息
 * 
 * 类比 Java：
 *   authService.register(userDTO)
 */
export function register(data) {
  return request({
    url: '/auth/register',
    method: 'post',
    data
  })
}

/**
 * 用户登录
 * 
 * @param {Object} data - 登录数据
 * @param {string} data.username - 用户名
 * @param {string} data.password - 密码
 * @returns {Promise} 返回 JWT 令牌
 * 
 * 类比 Java：
 *   authService.login(username, password)
 */
export function login(data) {
  return request({
    url: '/auth/login',
    method: 'post',
    data
  })
}

/**
 * 用户登出
 * 
 * @returns {Promise} 返回成功消息
 * 
 * 类比 Java：
 *   authService.logout()
 * 
 * 注意：
 *   这个请求需要携带 JWT 令牌
 *   request 拦截器会自动添加 Authorization header
 */
export function logout() {
  return request({
    url: '/auth/logout',
    method: 'post'
  })
}

/**
 * 获取当前用户信息
 * 
 * @returns {Promise} 返回用户信息
 * 
 * 类比 Java：
 *   userService.getCurrentUser()
 * 
 * 注意：此函数已移至 user.js，这里保留是为了向后兼容
 */
export function getCurrentUser() {
  return getUserInfo()
}
