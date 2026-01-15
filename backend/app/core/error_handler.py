"""
统一错误处理工具

提供装饰器和工具函数，统一处理 API 端点的异常
"""
import logging
from functools import wraps
from typing import Callable, Any
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


def handle_api_errors(
    default_message: str = "操作失败",
    default_status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    log_error: bool = True
):
    """
    统一错误处理装饰器
    
    Args:
        default_message: 默认错误消息
        default_status_code: 默认状态码
        log_error: 是否记录错误日志
    
    使用示例:
        @router.get("/example")
        @handle_api_errors(default_message="获取数据失败")
        async def get_example():
            # 业务逻辑
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except HTTPException:
                # 重新抛出 HTTPException，保持原有行为
                raise
            except Exception as e:
                if log_error:
                    logger.error(f"{func.__name__} 执行失败: {e}", exc_info=True)
                raise HTTPException(
                    status_code=default_status_code,
                    detail=default_message if default_message else str(e)
                )
        return wrapper
    return decorator


def handle_sync_api_errors(
    default_message: str = "操作失败",
    default_status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    log_error: bool = True
):
    """
    同步函数的统一错误处理装饰器
    
    使用示例:
        @router.get("/example")
        @handle_sync_api_errors(default_message="获取数据失败")
        def get_example():
            # 业务逻辑
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except HTTPException:
                # 重新抛出 HTTPException，保持原有行为
                raise
            except Exception as e:
                if log_error:
                    logger.error(f"{func.__name__} 执行失败: {e}", exc_info=True)
                raise HTTPException(
                    status_code=default_status_code,
                    detail=default_message if default_message else str(e)
                )
        return wrapper
    return decorator

