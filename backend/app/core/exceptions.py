"""
自定义异常类

这些异常类用于统一处理应用中的各种错误情况
类比 Java：相当于 Spring 的 @ControllerAdvice + @ExceptionHandler
"""
import logging

logger = logging.getLogger(__name__)


class AppException(Exception):
    """
    应用基础异常
    
    所有自定义异常都继承此类
    类比 Java：相当于 RuntimeException
    """
    def __init__(self, message: str, status_code: int = 400, detail: str = None):
        self.message = message
        self.status_code = status_code
        self.detail = detail or message
        super().__init__(self.message)


# ==================== 认证异常 ====================

class AuthenticationException(AppException):
    """认证异常（401）"""
    def __init__(self, message: str = "认证失败", detail: str = None):
        super().__init__(message, status_code=401, detail=detail)


class InvalidCredentialsException(AuthenticationException):
    """用户名或密码错误"""
    def __init__(self):
        super().__init__("用户名或密码错误", detail="请检查用户名和密码是否正确")


class TokenExpiredException(AuthenticationException):
    """令牌已过期"""
    def __init__(self):
        super().__init__("令牌已过期", detail="请重新登录")


class TokenInvalidException(AuthenticationException):
    """令牌无效"""
    def __init__(self):
        super().__init__("令牌无效", detail="请重新登录")


# ==================== 授权异常 ====================

class AuthorizationException(AppException):
    """授权异常（403）"""
    def __init__(self, message: str = "权限不足", detail: str = None):
        super().__init__(message, status_code=403, detail=detail)


class UserBannedException(AuthorizationException):
    """用户已被封禁"""
    def __init__(self):
        super().__init__("用户已被封禁", detail="您的账号已被封禁，无法使用此功能")


class ForbiddenException(AuthorizationException):
    """禁止访问"""
    def __init__(self, message: str = "禁止访问"):
        super().__init__(message, detail=message)


# ==================== 资源异常 ====================

class ResourceNotFoundException(AppException):
    """资源不存在异常（404）"""
    def __init__(self, resource: str = "资源", resource_id: int = None):
        if resource_id:
            message = f"{resource}不存在"
            detail = f"ID 为 {resource_id} 的{resource}不存在"
        else:
            message = f"{resource}不存在"
            detail = message
        super().__init__(message, status_code=404, detail=detail)


# ==================== 业务逻辑异常 ====================

class BusinessLogicException(AppException):
    """业务逻辑异常（400）"""
    def __init__(self, message: str, detail: str = None):
        super().__init__(message, status_code=400, detail=detail)


class DuplicateActionException(BusinessLogicException):
    """重复操作异常"""
    def __init__(self, action: str):
        super().__init__(f"重复{action}", detail=f"您已经{action}过了，无需重复操作")


class ValidationException(BusinessLogicException):
    """数据验证异常"""
    def __init__(self, message: str, detail: str = None):
        super().__init__(message, detail=detail)


# ==================== 服务器异常 ====================

class InternalServerException(AppException):
    """服务器内部错误（500）"""
    def __init__(self, message: str = "服务器内部错误", detail: str = None):
        super().__init__(message, status_code=500, detail=detail)
        # 记录错误日志
        logger.error(f"服务器内部错误: {message}", exc_info=True)
