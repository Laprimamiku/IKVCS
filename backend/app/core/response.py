"""
统一响应格式

定义所有 API 接口的统一响应格式
类比 Java：相当于 Spring 的 ResponseEntity<T> 或统一响应包装类

使用方式：
    from app.core.response import success_response, error_response
    
    return success_response(data={"user_id": 1}, message="操作成功")
    return error_response(message="操作失败", status_code=400)
"""
from typing import Optional, Any, Dict
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ApiResponse(BaseModel):
    """
    统一 API 响应格式
    
    所有接口都应该返回此格式的响应
    类比 Java：
        public class ApiResponse<T> {
            private boolean success;
            private T data;
            private String message;
            private Integer statusCode;
        }
    """
    success: bool
    data: Optional[Any] = None
    message: Optional[str] = None
    status_code: int = 200
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {"id": 1, "name": "示例数据"},
                "message": "操作成功",
                "status_code": 200
            }
        }


def success_response(
    data: Any = None,
    message: str = "操作成功",
    status_code: int = 200
) -> JSONResponse:
    """
    成功响应
    
    Args:
        data: 响应数据
        message: 响应消息
        status_code: HTTP 状态码
        
    Returns:
        JSONResponse: FastAPI 响应对象
        
    使用示例：
        return success_response(data={"user_id": 1}, message="用户创建成功")
    """
    return JSONResponse(
        status_code=status_code,
        content={
            "success": True,
            "data": data,
            "message": message,
            "status_code": status_code
        }
    )


def error_response(
    message: str = "操作失败",
    detail: Optional[str] = None,
    status_code: int = 400
) -> JSONResponse:
    """
    错误响应
    
    Args:
        message: 错误消息
        detail: 详细错误信息
        status_code: HTTP 状态码
        
    Returns:
        JSONResponse: FastAPI 响应对象
        
    使用示例：
        return error_response(message="用户不存在", status_code=404)
    """
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "data": None,
            "message": message,
            "detail": detail or message,
            "status_code": status_code
        }
    )


def paginated_response(
    items: list,
    total: int,
    page: int,
    page_size: int,
    message: str = "查询成功"
) -> JSONResponse:
    """
    分页响应
    
    Args:
        items: 数据列表
        total: 总数
        page: 当前页
        page_size: 每页数量
        message: 响应消息
        
    Returns:
        JSONResponse: FastAPI 响应对象
        
    使用示例：
        return paginated_response(
            items=[{"id": 1}, {"id": 2}],
            total=100,
            page=1,
            page_size=20
        )
    """
    from math import ceil
    
    total_pages = ceil(total / page_size) if total > 0 else 0
    
    return JSONResponse(
        status_code=200,
        content={
            "success": True,
            "data": {
                "items": items,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages
            },
            "message": message,
            "status_code": 200
        }
    )

