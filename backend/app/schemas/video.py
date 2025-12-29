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


class VideoUpdateRequest(BaseModel):
    """
    视频更新请求
    
    用于编辑视频信息
    """
    title: Optional[str] = Field(default=None, max_length=100, description="视频标题")
    description: Optional[str] = Field(default=None, description="视频描述")
    category_id: Optional[int] = Field(default=None, description="分类ID")
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "更新后的标题",
                "description": "更新后的描述",
                "category_id": 1
            }
        }


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
    danmaku_count: int = 0
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


class VideoBrief(BaseModel):
    """
    视频简要信息
    
    用于收藏列表等场景展示基本视频信息
    """
    id: int
    title: str
    cover_url: Optional[str]
    duration: int
    view_count: int
    uploader: UploaderBriefResponse
    created_at: datetime
    
    class Config:
        from_attributes = True


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
    danmaku_count: int = 0
    uploader: UploaderBriefResponse
    category: CategoryBriefResponse
    created_at: datetime
    
    class Config:
        from_attributes = True

        

# ==================== 字幕和封面上传相关 ====================

class SubtitleUploadResponse(BaseModel):
    """字幕上传响应"""
    message: str
    subtitle_url: str
    video_id: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "字幕上传成功",
                "subtitle_url": "/uploads/subtitles/1_subtitle.srt",
                "video_id": 1
            }
        }


class CoverUploadResponse(BaseModel):
    """封面上传响应"""
    message: str
    cover_url: str
    video_id: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "封面上传成功",
                "cover_url": "/uploads/covers/1_cover.jpg",
                "video_id": 1
            }
        }


# ==================== 视频状态和转码测试相关 ====================

class VideoStatusResponse(BaseModel):
    """视频状态响应"""
    video_id: int
    title: str
    status: int
    status_text: str
    video_url: Optional[str]
    duration: int

    class Config:
        json_schema_extra = {
            "example": {
                "video_id": 1,
                "title": "测试视频",
                "status": 1,
                "status_text": "审核中",
                "video_url": "/videos/hls/1/master.m3u8",
                "duration": 120,
            }
        }


class TranscodeTestRequest(BaseModel):
    """
    转码测试请求（开发/调试专用）
    
    注意：此 Schema 仅用于开发和调试，生产环境应通过上传流程自动触发转码
    """
    video_id: int

    class Config:
        json_schema_extra = {"example": {"video_id": 1}}


class WatchHistoryResponse(BaseModel):
    """
    观看历史响应
    """
    id: int
    video_id: int
    watched_at: datetime
    video: Optional['VideoListItemResponse'] = None
    
    class Config:
        from_attributes = True


class TranscodeTestResponse(BaseModel):
    """
    转码测试响应（开发/调试专用）
    
    注意：此 Schema 仅用于开发和调试
    """
    message: str
    video_id: int
    status: str

    class Config:
        json_schema_extra = {
            "example": {
                "message": "转码任务已启动",
                "video_id": 1,
                "status": "transcoding"
            }
        }
