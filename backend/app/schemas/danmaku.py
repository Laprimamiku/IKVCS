"""
弹幕相关的 Pydantic Schema（DTO）

用于弹幕 API 的请求验证和响应序列化
"""
from pydantic import BaseModel, Field, field_serializer
from typing import Optional
from datetime import datetime
from app.utils.timezone_utils import isoformat_in_app_tz


# ==================== 请求模型 ====================

class DanmakuCreateRequest(BaseModel):
    """
    创建弹幕请求
    """
    content: str = Field(..., max_length=255, description="弹幕内容")
    video_time: float = Field(..., ge=0, description="视频时间轴位置（秒）")
    color: str = Field(default="#FFFFFF", description="弹幕颜色")


class DanmakuQueryRequest(BaseModel):
    """
    弹幕查询请求
    """
    video_id: int = Field(..., description="视频ID")
    start_time: Optional[float] = Field(default=None, ge=0, description="开始时间（秒）")
    end_time: Optional[float] = Field(default=None, ge=0, description="结束时间（秒）")


# ==================== 响应模型 ====================

class UserBriefInDanmaku(BaseModel):
    """弹幕中的用户简要信息"""
    id: int
    username: str
    nickname: str
    avatar: Optional[str] = None
    
    class Config:
        from_attributes = True


class DanmakuResponse(BaseModel):
    """
    弹幕响应模型（包含用户信息）
    """
    id: int
    video_id: int
    user_id: int
    content: str
    video_time: float
    color: str
    ai_score: Optional[int] = None
    ai_category: Optional[str] = None
    ai_reason: Optional[str] = None
    ai_confidence: Optional[float] = None
    ai_source: Optional[str] = None
    is_highlight: bool = False
    is_deleted: bool = False
    like_count: int = 0
    created_at: datetime
    user: Optional[UserBriefInDanmaku] = None  # 用户信息

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime) -> str:
        return isoformat_in_app_tz(value)
    
    class Config:
        from_attributes = True


class DanmakuListResponse(BaseModel):
    """
    弹幕列表响应
    """
    items: list[DanmakuResponse]
    total: int

