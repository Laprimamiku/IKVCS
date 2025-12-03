"""
自定义异常类
"""

class AppException(Exception):
    """应用基础异常"""
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code

# 认证异常
class AuthenticationException(AppException):
    def __init__(self, message: str = "认证失败"):
        super().__init__(message, status_code=401)

class InvalidCredentialsException(AuthenticationException):
    def __init__(self):
        super().__init__("用户名或密码错误")

class TokenExpiredException(AuthenticationException):
    def __init__(self):
        super().__init__("令牌已过期")

# 授权异常
class AuthorizationException(AppException):
    def __init__(self, message: str = "权限不足"):
        super().__init__(message, status_code=403)

class UserBannedException(AuthorizationException):
    def __init__(self):
        super().__init__("用户已被封禁")

# 资源异常
class ResourceNotFoundException(AppException):
    def __init__(self, resource: str):
        super().__init__(f"{resource}不存在", status_code=404)

# 业务逻辑异常
class BusinessLogicException(AppException):
    pass

class DuplicateActionException(BusinessLogicException):
    def __init__(self, action: str):
        super().__init__(f"重复{action}")

# TODO: 添加更多自定义异常类
