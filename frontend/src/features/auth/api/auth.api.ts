/**
 * 认证相关 API
 * 
 * 这个文件封装了所有认证相关的 API 请求
 * 相当于 Java 的 Service 接口调用
 */
import { request } from "@/shared/utils/request"
import { getCurrentUser as getUserInfo } from '@/features/user/api/user.api'
import type { ApiResponse } from "@/shared/types/entity"

export interface RegisterData {
  username: string
  password: string
  nickname: string
}

export interface LoginData {
  username: string
  password: string
}

export interface LoginResponse {
  access_token: string
  token_type?: string
}

/**
 * 用户注册
 * 
 * @param data - 注册数据
 * @returns 返回用户信息
 * 
 * 类比 Java：
 *   authService.register(userDTO)
 */
export function register(data: RegisterData) {
  return request.post<unknown>('/auth/register', data)
}

/**
 * 用户登录
 * 
 * @param data - 登录数据
 * @returns 返回 JWT 令牌
 * 
 * 类比 Java：
 *   authService.login(username, password)
 */
export function login(data: LoginData) {
  // request.post 会将返回包装为 ApiResponse<LoginResponse>
  return request.post<LoginResponse>('/auth/login', data)
}

/**
 * 用户登出
 * 
 * @returns 返回成功消息
 * 
 * 类比 Java：
 *   authService.logout()
 * 
 * 注意：
 *   这个请求需要携带 JWT 令牌
 *   request 拦截器会自动添加 Authorization header
 */
export function logout() {
  return request.post<ApiResponse>('/auth/logout')
}

/**
 * 获取当前用户信息
 * 
 * @returns 返回用户信息
 * 
 * 类比 Java：
 *   userService.getCurrentUser()
 * 
 * 注意：此函数已移至 user.ts，这里保留是为了向后兼容
 */
export function getCurrentUser() {
  return getUserInfo()
}

