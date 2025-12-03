"""
用户相关的 Pydantic 模型
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

# 请求模型
class UserRegisterRequest(BaseModel):
    """用户注册请求"""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    nickname: str = Field(..., min_length=1, max_length=50)

class UserLoginRequest(BaseModel):
    """用户登录请求"""
    username: str
    password: str

class UserUpdateRequest(BaseModel):
    """用户信息更新请求"""
    nickname: Optional[str] = Field(None, min_length=1, max_length=50)
    intro: Optional[str] = Field(None, max_length=500)

# 响应模型
class UserResponse(BaseModel):
    """用户信息响应"""
    id: int
    username: str
    nickname: str
    avatar: Optional[str]
    intro: Optional[str]
    role: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class UserBriefResponse(BaseModel):
    """用户简要信息响应"""
    id: int
    username: str
    nickname: str
    avatar: Optional[str]
    
    class Config:
        from_attributes = True
