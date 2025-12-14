# backend/app/schemas/category.py

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

# ==================== 基础模型 ====================
class CategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=50, description="分类名称")
    description: Optional[str] = Field(None, max_length=255, description="分类描述")

# ==================== 请求模型 ====================
class CategoryCreate(CategoryBase):
    """创建分类请求"""
    pass

class CategoryUpdate(BaseModel):
    """更新分类请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    description: Optional[str] = Field(None, max_length=255)

# ==================== 响应模型 ====================
class CategoryResponse(CategoryBase):
    """分类响应信息"""
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class CategoryListResponse(BaseModel):
    items: List[CategoryResponse]
    total: int