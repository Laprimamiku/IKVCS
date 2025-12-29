"""
用户相关的 Pydantic Schema

这个文件的作用：
1. 定义 API 请求和响应的数据格式
2. 自动验证数据（类型、长度、格式等）
3. 自动生成 API 文档

类比 Java：
    相当于 Spring Boot 的 DTO（Data Transfer Object）
    
需求：1.1-1.5, 2.1-2.4
"""
from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime


# ============================================
# 用户注册相关 Schema
# ============================================

class UserRegisterRequest(BaseModel):
    """
    用户注册请求
    
    类比 Java：
        @Data
        public class UserRegisterDTO {
            @NotBlank
            @Size(min=3, max=50)
            private String username;
            
            @NotBlank
            @Size(min=6, max=50)
            private String password;
            
            @NotBlank
            @Size(min=2, max=50)
            private String nickname;
        }
    """
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    password: str = Field(..., min_length=6, max_length=50, description="密码")
    nickname: str = Field(..., min_length=2, max_length=50, description="昵称")
    
    @validator('username')
    def username_alphanumeric(cls, v):
        """验证用户名只能包含字母、数字、下划线"""
        if not v.replace('_', '').isalnum():
            raise ValueError('用户名只能包含字母、数字、下划线')
        return v
    
    class Config:
        # 示例数据（用于 API 文档）
        json_schema_extra = {
            "example": {
                "username": "zhangsan",
                "password": "123456",
                "nickname": "张三"
            }
        }


# ============================================
# 用户登录相关 Schema
# ============================================

class UserLoginRequest(BaseModel):
    """
    用户登录请求
    
    类比 Java：
        @Data
        public class UserLoginDTO {
            @NotBlank
            private String username;
            
            @NotBlank
            private String password;
        }
    """
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")
    
    class Config:
        json_schema_extra = {
            "example": {
                "username": "zhangsan",
                "password": "123456"
            }
        }


class TokenResponse(BaseModel):
    """
    JWT 令牌响应
    
    类比 Java：
        @Data
        public class TokenDTO {
            private String accessToken;
            private String tokenType;
        }
    """
    access_token: str = Field(..., description="访问令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
    
    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer"
            }
        }


# ============================================
# 用户信息相关 Schema
# ============================================

class UserResponse(BaseModel):
    """
    用户信息响应（返回给前端）
    
    类比 Java：
        @Data
        public class UserVO {
            private Integer id;
            private String username;
            private String nickname;
            private String avatar;
            private String intro;
            private String role;
            private Integer status;
            private LocalDateTime lastLoginTime;
            private LocalDateTime createdAt;
        }
    
    为什么不返回 password_hash？
        密码哈希是敏感信息，不应该返回给前端
    """
    id: int
    username: str
    nickname: str
    avatar: Optional[str] = None
    intro: Optional[str] = None
    role: str
    status: int
    last_login_time: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        # 允许从 ORM 模型创建（User 模型 → UserResponse）
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "username": "zhangsan",
                "nickname": "张三",
                "avatar": None,  # 示例：未设置头像时返回 None
                "intro": "这是我的个人简介",
                "role": "user",
                "status": 1,
                "last_login_time": "2024-01-01T12:00:00",
                "created_at": "2024-01-01T10:00:00"
            }
        }


class UserBriefResponse(BaseModel):
    """
    用户简要信息响应（用于列表展示）
    
    为什么需要简要信息？
        在评论、弹幕等场景，不需要返回完整的用户信息
        只返回必要的字段，减少数据传输量
    """
    id: int
    username: str
    nickname: str
    avatar: Optional[str] = None
    
    class Config:
        from_attributes = True


class UserUpdateRequest(BaseModel):
    """
    用户信息更新请求
    
    为什么所有字段都是 Optional？
        用户可能只想更新部分信息（如只更新昵称）
        不传的字段保持原值
    """
    nickname: Optional[str] = Field(None, min_length=2, max_length=50)
    avatar: Optional[str] = Field(None, max_length=255)
    intro: Optional[str] = Field(None, max_length=500)
    
    class Config:
        json_schema_extra = {
            "example": {
                "nickname": "新昵称",
                "intro": "更新后的个人简介"
            }
        }


# ============================================
# 通用响应 Schema
# ============================================

class MessageResponse(BaseModel):
    """
    通用消息响应
    
    用于返回简单的成功/失败消息
    
    类比 Java：
        @Data
        public class MessageDTO {
            private String message;
        }
    """
    message: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "操作成功"
            }
        }

