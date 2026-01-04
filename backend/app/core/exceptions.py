"""
自定义异常类

这些异常类用于统一处理应用中的各种错误情况
类比 Java：相当于 Spring 的 @ControllerAdvice + @ExceptionHandler
"""
import logging
from typing import Optional

from app.core.error_codes import ErrorCode, get_error_message

logger = logging.getLogger(__name__)


class AppException(Exception):
    """
    应用基础异常
    
    所有自定义异常都继承此类
    类比 Java：相当于 RuntimeException
    """
    def __init__(
        self,
        message: str,
        status_code: int = 400,
        detail: Optional[str] = None,
        error_code: Optional[ErrorCode] = None
    ):
        self.message = message
        self.status_code = status_code
        self.detail = detail or message
        self.error_code = error_code or ErrorCode.UNKNOWN_ERROR
        super().__init__(self.message)


# ==================== 认证异常 ====================

class AuthenticationException(AppException):
    """认证异常（401）"""
    def __init__(self, message: str = "认证失败", detail: str = None, error_code: ErrorCode = ErrorCode.AUTH_FAILED):
        super().__init__(message, status_code=401, detail=detail, error_code=error_code)


class InvalidCredentialsException(AuthenticationException):
    """用户名或密码错误"""
    def __init__(self):
        super().__init__(
            get_error_message(ErrorCode.INVALID_CREDENTIALS),
            detail="请检查用户名和密码是否正确",
            error_code=ErrorCode.INVALID_CREDENTIALS
        )


class TokenExpiredException(AuthenticationException):
    """令牌已过期"""
    def __init__(self):
        super().__init__(
            get_error_message(ErrorCode.TOKEN_EXPIRED),
            detail="请重新登录",
            error_code=ErrorCode.TOKEN_EXPIRED
        )


class TokenInvalidException(AuthenticationException):
    """令牌无效"""
    def __init__(self):
        super().__init__(
            get_error_message(ErrorCode.TOKEN_INVALID),
            detail="请重新登录",
            error_code=ErrorCode.TOKEN_INVALID
        )


# ==================== 授权异常 ====================

class AuthorizationException(AppException):
    """授权异常（403）"""
    def __init__(self, message: str = "权限不足", detail: str = None, error_code: ErrorCode = ErrorCode.FORBIDDEN):
        super().__init__(message, status_code=403, detail=detail, error_code=error_code)


class UserBannedException(AuthorizationException):
    """用户已被封禁"""
    def __init__(self):
        super().__init__(
            get_error_message(ErrorCode.USER_BANNED),
            detail="您的账号已被封禁，无法使用此功能",
            error_code=ErrorCode.USER_BANNED
        )


class ForbiddenException(AuthorizationException):
    """禁止访问"""
    def __init__(self, message: str = "禁止访问", error_code: ErrorCode = ErrorCode.ACCESS_DENIED):
        super().__init__(message, detail=message, error_code=error_code)


# ==================== 资源异常 ====================

class ResourceNotFoundException(AppException):
    """资源不存在异常（404）"""
    def __init__(self, resource: str = "资源", resource_id: int = None, error_code: ErrorCode = ErrorCode.RESOURCE_NOT_FOUND):
        if resource_id:
            message = f"{resource}不存在"
            detail = f"ID 为 {resource_id} 的{resource}不存在"
        else:
            message = f"{resource}不存在"
            detail = message
        
        # 根据资源类型选择对应的错误码
        resource_lower = resource.lower()
        if "视频" in resource_lower or "video" in resource_lower:
            error_code = ErrorCode.VIDEO_NOT_FOUND
        elif "用户" in resource_lower or "user" in resource_lower:
            error_code = ErrorCode.USER_NOT_FOUND
        elif "评论" in resource_lower or "comment" in resource_lower:
            error_code = ErrorCode.COMMENT_NOT_FOUND
        elif "分类" in resource_lower or "category" in resource_lower:
            error_code = ErrorCode.CATEGORY_NOT_FOUND
        
        super().__init__(message, status_code=404, detail=detail, error_code=error_code)


# ==================== 业务逻辑异常 ====================

class BusinessLogicException(AppException):
    """业务逻辑异常（400）"""
    def __init__(self, message: str, detail: str = None, error_code: ErrorCode = ErrorCode.OPERATION_FAILED):
        super().__init__(message, status_code=400, detail=detail, error_code=error_code)


class DuplicateActionException(BusinessLogicException):
    """重复操作异常"""
    def __init__(self, action: str):
        super().__init__(
            f"重复{action}",
            detail=f"您已经{action}过了，无需重复操作",
            error_code=ErrorCode.DUPLICATE_ACTION
        )


class ValidationException(BusinessLogicException):
    """数据验证异常"""
    def __init__(self, message: str, detail: str = None):
        super().__init__(message, detail=detail, error_code=ErrorCode.VALIDATION_FAILED)


# ==================== 服务器异常 ====================

class InternalServerException(AppException):
    """服务器内部错误（500）"""
    def __init__(self, message: str = "服务器内部错误", detail: str = None, error_code: ErrorCode = ErrorCode.INTERNAL_ERROR):
        super().__init__(message, status_code=500, detail=detail, error_code=error_code)
        # 记录错误日志
        logger.error(f"服务器内部错误: {message}", exc_info=True)
