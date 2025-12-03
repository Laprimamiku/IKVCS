/**
 * Axios 请求封装
 * 
 * 这个文件的作用：
 * 1. 统一配置 API 基础 URL
 * 2. 自动添加 JWT 令牌到请求头
 * 3. 统一处理响应错误
 * 
 * 相当于 Java 的 RestTemplate + 拦截器
 */
import axios from 'axios'
import { ElMessage } from 'element-plus'

// 创建 axios 实例
const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1',
  timeout: 10000, // 请求超时时间（10秒）
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器（发送请求前执行）
// 相当于 Spring 的 HandlerInterceptor.preHandle()
request.interceptors.request.use(
  config => {
    // 自动添加 JWT 令牌到请求头
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    
    console.log('📤 发送请求:', config.method.toUpperCase(), config.url)
    return config
  },
  error => {
    console.error('❌ 请求错误:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器（收到响应后执行）
// 相当于 Spring 的 HandlerInterceptor.postHandle()
request.interceptors.response.use(
  response => {
    console.log('📥 收到响应:', response.config.url, response.status)
    
    // 直接返回 data 部分（简化使用）
    return response.data
  },
  error => {
    console.error('❌ 响应错误:', error)
    
    // 统一错误处理
    if (error.response) {
      const { status, data } = error.response
      
      switch (status) {
        case 401:
          // 未授权：令牌过期或无效
          ElMessage.error('登录已过期，请重新登录')
          localStorage.removeItem('access_token')
          // 跳转到登录页
          window.location.href = '/login'
          break
        
        case 403:
          // 禁止访问：权限不足
          ElMessage.error('权限不足')
          break
        
        case 404:
          // 资源不存在
          ElMessage.error('请求的资源不存在')
          break
        
        case 500:
          // 服务器错误
          ElMessage.error('服务器错误，请稍后重试')
          break
        
        default:
          // 其他错误
          ElMessage.error(data?.message || '请求失败')
      }
    } else if (error.request) {
      // 请求已发送但没有收到响应
      ElMessage.error('网络错误，请检查网络连接')
    } else {
      // 其他错误
      ElMessage.error('请求失败：' + error.message)
    }
    
    return Promise.reject(error)
  }
)

export default request
