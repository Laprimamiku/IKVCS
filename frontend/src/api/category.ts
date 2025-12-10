// src/api/category.ts
import { request } from '@/utils/request';
import type { Category } from '@/types/entity';

/**
 * 获取所有分类
 */
export function getCategories() {
  return request.get<Category[]>('/categories');
}

/**
 * 创建分类（管理员）
 */
export function createCategory(data: { name: string; description?: string }) {
  return request.post<Category>('/categories/admin', data);
}