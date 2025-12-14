# from typing import Optional, List
# from pydantic import BaseModel
# from datetime import datetime
# from app.schemas.video import VideoBrief  # 需要运行时导入，用于 Pydantic 解析前向引用

# # --- 点赞相关 ---
# class LikeCreate(BaseModel):
#     target_id: int
#     target_type: str # "video" or "comment"

# class LikeStatus(BaseModel):
#     is_liked: bool
#     like_count: int

# # --- 收藏相关 ---
# class CollectionCreate(BaseModel):
#     video_id: int

# class CollectionStatus(BaseModel):
#     is_collected: bool
    
# class CollectionResponse(BaseModel):
#     id: int
#     video_id: int
#     created_at: datetime
#     video: Optional['VideoBrief'] = None # 用于收藏列表展示视频信息

#     class Config:
#         from_attributes = True


# backend/app/schemas/interaction.py

from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime

# ==================== 点赞 Schema ====================
class LikeCreate(BaseModel):
    target_type: str = Field(..., description="目标类型: VIDEO, COMMENT")
    target_id: int = Field(..., description="目标ID")

    @validator('target_type')
    def validate_type(cls, v):
        if v not in ['VIDEO', 'COMMENT']:
            raise ValueError('Invalid target type')
        return v

class LikeStatus(BaseModel):
    is_liked: bool
    like_count: int

# ==================== 收藏 Schema ====================
class CollectionCreate(BaseModel):
    video_id: int = Field(..., description="视频ID")

class CollectionStatus(BaseModel):
    is_collected: bool

class CollectionResponse(BaseModel):
    id: int
    user_id: int
    video_id: int
    created_at: datetime
    
    # 如果需要返回视频简要信息，可以在这里嵌套 VideoBriefResponse
    # video: VideoBriefResponse 
    
    class Config:
        from_attributes = True

# ==================== 举报 Schema (新增) ====================
class ReportCreate(BaseModel):
    """创建举报请求"""
    target_type: str = Field(..., description="举报目标类型: VIDEO, COMMENT, DANMAKU")
    target_id: int = Field(..., description="目标ID")
    reason: str = Field(..., min_length=1, max_length=100, description="举报原因")
    description: Optional[str] = Field(None, max_length=500, description="详细描述")

    @validator('target_type')
    def validate_report_target(cls, v):
        allowed = ['VIDEO', 'COMMENT', 'DANMAKU']
        if v not in allowed:
            raise ValueError(f"Invalid target type. Must be one of {allowed}")
        return v