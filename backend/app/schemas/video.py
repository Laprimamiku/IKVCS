"""
视频相关的 Pydantic Schema（DTO）

这些 Schema 用于：
1. API 请求验证
2. API 响应序列化
3. 数据传输对象（DTO）

相当于 Java 的 DTO 类
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ==================== 请求模型 ====================

class VideoListRequest(BaseModel):
    """
    视频列表查询请求
    
    查询参数：
    - page: 页码（从1开始）
    - page_size: 每页数量
    - category_id: 分类ID（可选）
    - keyword: 搜索关键词（可选）
    """
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")
    category_id: Optional[int] = Field(default=None, description="分类ID")
    keyword: Optional[str] = Field(default=None, max_length=100, description="搜索关键词")


# ==================== 响应模型 ====================

class UploaderBriefResponse(BaseModel):
    """上传者简要信息"""
    id: int
    username: str
    nickname: str
    avatar: Optional[str]
    
    class Config:
        from_attributes = True


class CategoryBriefResponse(BaseModel):
    """分类简要信息"""
    id: int
    name: str
    
    class Config:
        from_attributes = True


class VideoListItemResponse(BaseModel):
    """
    视频列表项响应
    
    用于视频列表展示，包含基本信息
    """
    id: int
    title: str
    description: Optional[str]
    cover_url: Optional[str]
    duration: int
    view_count: int
    like_count: int
    collect_count: int
    uploader: UploaderBriefResponse
    category: CategoryBriefResponse
    created_at: datetime
    
    class Config:
        from_attributes = True


class VideoListResponse(BaseModel):
    """
    视频列表响应（分页）
    
    包含：
    - items: 视频列表
    - total: 总数
    - page: 当前页
    - page_size: 每页数量
    - total_pages: 总页数
    """
    items: list[VideoListItemResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class VideoDetailResponse(BaseModel):
    """
    视频详情响应
    
    包含完整的视频信息，包括播放地址
    """
    id: int
    title: str
    description: Optional[str]
    cover_url: Optional[str]
    video_url: Optional[str]  # m3u8 播放地址
    subtitle_url: Optional[str]  # 字幕文件地址
    duration: int
    status: int
    view_count: int
    like_count: int
    collect_count: int
    uploader: UploaderBriefResponse
    category: CategoryBriefResponse
    created_at: datetime
    
    class Config:
        from_attributes = True
