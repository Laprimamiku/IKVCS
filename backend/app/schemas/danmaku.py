"""
弹幕相关的 Pydantic Schema（DTO）

用于弹幕 API 的请求验证和响应序列化
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


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

class DanmakuResponse(BaseModel):
    """
    弹幕响应模型
    """
    id: int
    video_id: int
    user_id: int
    content: str
    video_time: float
    color: str
    ai_score: Optional[int] = None
    ai_category: Optional[str] = None
    is_highlight: bool = False
    created_at: datetime
    
    class Config:
        from_attributes = True


class DanmakuListResponse(BaseModel):
    """
    弹幕列表响应
    """
    items: list[DanmakuResponse]
    total: int

