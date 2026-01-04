"""
统一错误码定义

定义所有业务错误码，确保前后端一致
类比 Java：相当于枚举类 ErrorCode
"""
from enum import IntEnum


class ErrorCode(IntEnum):
    """统一错误码枚举"""
    
    # ==================== 通用错误 (1000-1999) ====================
    SUCCESS = 0  # 成功
    UNKNOWN_ERROR = 1000  # 未知错误
    INVALID_PARAMETER = 1001  # 参数无效
    MISSING_PARAMETER = 1002  # 缺少参数
    OPERATION_FAILED = 1003  # 操作失败
    
    # ==================== 认证错误 (2000-2999) ====================
    AUTH_FAILED = 2000  # 认证失败
    INVALID_CREDENTIALS = 2001  # 用户名或密码错误
    TOKEN_EXPIRED = 2002  # 令牌已过期
    TOKEN_INVALID = 2003  # 令牌无效
    TOKEN_MISSING = 2004  # 令牌缺失
    
    # ==================== 授权错误 (3000-3999) ====================
    FORBIDDEN = 3000  # 权限不足
    USER_BANNED = 3001  # 用户已被封禁
    ACCESS_DENIED = 3002  # 访问被拒绝
    
    # ==================== 资源错误 (4000-4999) ====================
    RESOURCE_NOT_FOUND = 4000  # 资源不存在
    VIDEO_NOT_FOUND = 4001  # 视频不存在
    USER_NOT_FOUND = 4002  # 用户不存在
    COMMENT_NOT_FOUND = 4003  # 评论不存在
    CATEGORY_NOT_FOUND = 4004  # 分类不存在
    
    # ==================== 业务逻辑错误 (5000-5999) ====================
    DUPLICATE_ACTION = 5000  # 重复操作
    VALIDATION_FAILED = 5001  # 数据验证失败
    UPLOAD_FAILED = 5002  # 上传失败
    TRANSCODE_FAILED = 5003  # 转码失败
    REVIEW_FAILED = 5004  # 审核失败
    
    # ==================== 服务器错误 (9000-9999) ====================
    INTERNAL_ERROR = 9000  # 服务器内部错误
    DATABASE_ERROR = 9001  # 数据库错误
    REDIS_ERROR = 9002  # Redis错误
    EXTERNAL_SERVICE_ERROR = 9003  # 外部服务错误


# 错误码到消息的映射
ERROR_MESSAGES = {
    ErrorCode.SUCCESS: "操作成功",
    ErrorCode.UNKNOWN_ERROR: "未知错误",
    ErrorCode.INVALID_PARAMETER: "参数无效",
    ErrorCode.MISSING_PARAMETER: "缺少参数",
    ErrorCode.OPERATION_FAILED: "操作失败",
    
    ErrorCode.AUTH_FAILED: "认证失败",
    ErrorCode.INVALID_CREDENTIALS: "用户名或密码错误",
    ErrorCode.TOKEN_EXPIRED: "令牌已过期，请重新登录",
    ErrorCode.TOKEN_INVALID: "令牌无效，请重新登录",
    ErrorCode.TOKEN_MISSING: "令牌缺失，请先登录",
    
    ErrorCode.FORBIDDEN: "权限不足",
    ErrorCode.USER_BANNED: "用户已被封禁",
    ErrorCode.ACCESS_DENIED: "访问被拒绝",
    
    ErrorCode.RESOURCE_NOT_FOUND: "资源不存在",
    ErrorCode.VIDEO_NOT_FOUND: "视频不存在",
    ErrorCode.USER_NOT_FOUND: "用户不存在",
    ErrorCode.COMMENT_NOT_FOUND: "评论不存在",
    ErrorCode.CATEGORY_NOT_FOUND: "分类不存在",
    
    ErrorCode.DUPLICATE_ACTION: "重复操作",
    ErrorCode.VALIDATION_FAILED: "数据验证失败",
    ErrorCode.UPLOAD_FAILED: "上传失败",
    ErrorCode.TRANSCODE_FAILED: "转码失败",
    ErrorCode.REVIEW_FAILED: "审核失败",
    
    ErrorCode.INTERNAL_ERROR: "服务器内部错误",
    ErrorCode.DATABASE_ERROR: "数据库错误",
    ErrorCode.REDIS_ERROR: "Redis错误",
    ErrorCode.EXTERNAL_SERVICE_ERROR: "外部服务错误",
}


def get_error_message(error_code: ErrorCode) -> str:
    """获取错误码对应的消息"""
    return ERROR_MESSAGES.get(error_code, "未知错误")

