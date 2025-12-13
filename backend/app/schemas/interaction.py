from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
from app.schemas.video import VideoBrief  # 需要运行时导入，用于 Pydantic 解析前向引用

# --- 点赞相关 ---
class LikeCreate(BaseModel):
    target_id: int
    target_type: str # "video" or "comment"

class LikeStatus(BaseModel):
    is_liked: bool
    like_count: int

# --- 收藏相关 ---
class CollectionCreate(BaseModel):
    video_id: int

class CollectionStatus(BaseModel):
    is_collected: bool
    
class CollectionResponse(BaseModel):
    id: int
    video_id: int
    created_at: datetime
    video: Optional['VideoBrief'] = None # 用于收藏列表展示视频信息

    class Config:
        from_attributes = True
