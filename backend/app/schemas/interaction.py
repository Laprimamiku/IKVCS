"""
互动相关的 Pydantic Schema（DTO）

用于点赞、收藏等互动功能的请求验证和响应序列化

注意：当前 interaction 模型还未完全实现，此 schema 为预留结构
"""
from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime


# ==================== 请求模型 ====================

class LikeRequest(BaseModel):
    """
    点赞请求
    """
    target_type: Literal["VIDEO", "COMMENT"] = Field(..., description="目标类型")
    target_id: int = Field(..., description="目标ID")


class CollectionRequest(BaseModel):
    """
    收藏请求
    """
    video_id: int = Field(..., description="视频ID")


# ==================== 响应模型 ====================

class LikeResponse(BaseModel):
    """
    点赞响应
    """
    id: int
    user_id: int
    target_type: str
    target_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class CollectionResponse(BaseModel):
    """
    收藏响应
    """
    id: int
    user_id: int
    video_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class InteractionStatsResponse(BaseModel):
    """
    互动统计响应
    """
    like_count: int = Field(default=0, description="点赞数")
    collect_count: int = Field(default=0, description="收藏数")
    is_liked: bool = Field(default=False, description="当前用户是否已点赞")
    is_collected: bool = Field(default=False, description="当前用户是否已收藏")

