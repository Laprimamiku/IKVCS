"""
评论相关的 Pydantic 模型
"""
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
# [修正点 1] 导入正确的类名 UserBriefResponse
from app.schemas.user import UserBriefResponse

# --- 基础模型 ---
class CommentBase(BaseModel):
    content: str = Field(..., min_length=1, max_length=1000, description="评论内容")

# --- 创建模型 ---
class CommentCreate(CommentBase):
    parent_id: Optional[int] = Field(None, description="父评论ID，如果是回复则必填")
    reply_to_user_id: Optional[int] = Field(None, description="回复目标用户ID（用于@功能）")

# --- 更新模型 ---
class CommentUpdate(BaseModel):
    content: Optional[str] = Field(None, min_length=1, max_length=1000)

# --- 响应模型 ---
class CommentResponse(CommentBase):
    id: int
    video_id: int
    user_id: int
    parent_id: Optional[int] = None
    reply_to_user_id: Optional[int] = None
    like_count: int
    created_at: datetime
    
    # [修正点 2] 使用正确的类型注解 UserBriefResponse
    user: Optional[UserBriefResponse] = None
    reply_to_user: Optional[UserBriefResponse] = None
    
    # AI 分析字段
    ai_score: Optional[int] = None
    ai_label: Optional[str] = None
    
    # 子评论预览 (用于列表展示)
    reply_count: int = 0
    replies: List['CommentResponse'] = []  # 嵌套结构

    class Config:
        from_attributes = True

# 解决嵌套引用
CommentResponse.model_rebuild()