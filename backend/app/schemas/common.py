"""
通用响应模型

提供分页、通用响应等共享的 Schema
"""
from pydantic import BaseModel, Field
from typing import Generic, TypeVar, List, Optional

T = TypeVar('T')


class PageResult(BaseModel, Generic[T]):
    """
    分页结果响应
    
    通用分页响应结构，可用于任何列表查询
    """
    items: List[T] = Field(..., description="数据列表")
    total: int = Field(..., ge=0, description="总记录数")
    page: int = Field(..., ge=1, description="当前页码")
    page_size: int = Field(..., ge=1, description="每页数量")
    total_pages: int = Field(..., ge=0, description="总页数")
    
    @classmethod
    def create(cls, items: List[T], total: int, page: int, page_size: int) -> "PageResult[T]":
        """
        创建分页结果
        
        Args:
            items: 数据列表
            total: 总记录数
            page: 当前页码
            page_size: 每页数量
            
        Returns:
            PageResult: 分页结果对象
        """
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )


class ApiResponse(BaseModel, Generic[T]):
    """
    通用 API 响应
    
    统一 API 响应格式
    """
    success: bool = Field(default=True, description="是否成功")
    message: Optional[str] = Field(default=None, description="响应消息")
    data: Optional[T] = Field(default=None, description="响应数据")
    
    @classmethod
    def success_response(cls, data: T = None, message: str = "操作成功") -> "ApiResponse[T]":
        """
        创建成功响应
        
        Args:
            data: 响应数据
            message: 响应消息
            
        Returns:
            ApiResponse: 成功响应对象
        """
        return cls(success=True, message=message, data=data)
    
    @classmethod
    def error_response(cls, message: str, data: T = None) -> "ApiResponse[T]":
        """
        创建错误响应
        
        Args:
            message: 错误消息
            data: 响应数据（可选）
            
        Returns:
            ApiResponse: 错误响应对象
        """
        return cls(success=False, message=message, data=data)

