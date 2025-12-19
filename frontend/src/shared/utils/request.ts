import axios from 'axios';
import type { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';
import { ElMessage } from 'element-plus';
import type { ApiResponse } from "@/shared/types/entity";

// 扩展 AxiosRequestConfig
interface RequestConfig extends AxiosRequestConfig {
  silent?: boolean;
}

// 从环境变量读取 API 基础 URL，开发环境提供默认值
const getBaseURL = (): string => {
  const envURL = import.meta.env.VITE_API_BASE_URL;
  if (envURL) {
    return envURL;
  }
  // 开发环境默认值（生产环境必须配置 VITE_API_BASE_URL）
  if (import.meta.env.DEV) {
    return 'http://localhost:8000/api/v1';
  }
  throw new Error('VITE_API_BASE_URL 环境变量未配置');
};

const service: AxiosInstance = axios.create({
  baseURL: getBaseURL(),
  timeout: 120000,
  headers: {
    'Content-Type': 'application/json'
  }
});

// 请求拦截器
service.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    console.error('📤 请求错误:', error);
    return Promise.reject(error);
  }
);

// 响应拦截器
service.interceptors.response.use(
  // @ts-ignore 忽略类型检查，允许直接返回 data
  (response: AxiosResponse) => {
    const payload = response.data;
    
    // 兼容处理：如果后端返回的是数组或已经包含 success 字段
    if (payload && typeof payload === 'object') {
        if (Array.isArray(payload)) {
            return { success: true, data: payload } as any;
        }
        if ('success' in payload) {
            return payload as any;
        }
    }
    
    // 默认包装
    return {
      success: true,
      data: payload,
      message: 'success'
    } as any;
  },
  (error: any) => {
    console.error('📥 响应错误:', error);
    if (error.response) {
      const { status, data } = error.response;
      const msg = data?.detail || data?.message || '请求失败';
      
      if (status === 401) {
        ElMessage.error('登录已过期，请重新登录');
        localStorage.removeItem('access_token');
      } else {
        ElMessage.error(msg);
      }
    } else {
      ElMessage.error('网络错误，请检查网络连接');
    }
    return Promise.reject(error);
  }
);

// 封装通用请求方法
export const request = {
  get<T = any>(url: string, config?: RequestConfig): Promise<ApiResponse<T>> {
    return service.get(url, config) as unknown as Promise<ApiResponse<T>>;
  },
  post<T = any>(url: string, data?: any, config?: RequestConfig): Promise<ApiResponse<T>> {
    return service.post(url, data, config) as unknown as Promise<ApiResponse<T>>;
  },
  put<T = any>(url: string, data?: any, config?: RequestConfig): Promise<ApiResponse<T>> {
    return service.put(url, data, config) as unknown as Promise<ApiResponse<T>>;
  },
  delete<T = any>(url: string, config?: RequestConfig): Promise<ApiResponse<T>> {
    return service.delete(url, config) as unknown as Promise<ApiResponse<T>>;
  }
};

export default service;

