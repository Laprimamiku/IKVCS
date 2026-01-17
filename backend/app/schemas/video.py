"""
视频相关的 Pydantic Schema（DTO）

这些 Schema 用于：
1. API 请求验证
2. API 响应序列化
3. 数据传输对象（DTO）

相当于 Java 的 DTO 类
"""
from pydantic import BaseModel, Field, field_serializer
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.utils.timezone_utils import isoformat_in_app_tz
from app.core.app_constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE


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
    page_size: int = Field(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="每页数量")
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
    is_following: Optional[bool] = None  # 当前用户是否关注了该UP主（仅在有登录用户时返回）
    
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
    video_url: Optional[str] = None  # 视频 URL（m3u8 格式）
    subtitle_url: Optional[str] = None  # 字幕文件 URL
    duration: int
    status: Optional[int] = None  # 视频状态：参考 VideoStatus 枚举（0=转码中, 1=审核中, 2=已发布, 3=已拒绝, 4=已删除）
    view_count: int
    like_count: int
    collect_count: int
    comment_count: int = 0
    danmaku_count: int = 0
    uploader: UploaderBriefResponse
    category: CategoryBriefResponse
    created_at: datetime

    @field_serializer('created_at')
    def serialize_created_at(self, value: datetime) -> str:
        return isoformat_in_app_tz(value)
    
    class Config:
        from_attributes = True


class AdminVideoListItemResponse(VideoListItemResponse):
    """
    管理员视频列表项响应
    
    包含审核相关字段，用于管理员后台
    """
    status: Optional[int] = None  # 视频状态：参考 VideoStatus 枚举（0=转码中, 1=审核中, 2=已发布, 3=已拒绝, 4=已删除）
    review_score: Optional[int] = None  # 综合审核评分（0-100）
    review_status: Optional[int] = None  # 审核状态：参考 ReviewStatus 枚举（0=待审核，1=通过，2=拒绝）
    review_report: Optional[dict] = None  # 审核报告详情（JSON格式）
    # 举报相关派生字段
    is_reported: bool = False  # 是否有待处理的举报
    open_report_count: int = 0  # 待处理举报数量
    last_reported_at: Optional[datetime] = None  # 最近举报时间
    
    class Config:
        from_attributes = True


class AdminVideoListResponse(BaseModel):
    """
    管理员视频列表响应（分页）
    
    包含审核相关字段
    """
    items: list[AdminVideoListItemResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


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
    
    @field_serializer('created_at')
    def serialize_created_at(self, value: datetime) -> str:
        """序列化时间为 ISO 格式（默认输出北京时间 +08:00）"""
        return isoformat_in_app_tz(value)
    
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
    comment_count: int = 0
    danmaku_count: int = 0
    uploader: UploaderBriefResponse
    category: CategoryBriefResponse
    created_at: datetime
    tags: Optional[list[dict[str, Any]]] = []  # 视频标签列表
    
    @field_serializer('created_at')
    def serialize_created_at(self, value: datetime) -> str:
        """序列化时间为 ISO 格式（默认输出北京时间 +08:00）"""
        return isoformat_in_app_tz(value)
    
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


class SubtitleListItem(BaseModel):
    """字幕列表条目"""
    url: str
    filename: str
    source: str  # manual / ai / legacy
    is_active: bool = False
    created_at: Optional[str] = None
    exists: bool = True


class SubtitleListResponse(BaseModel):
    """字幕列表响应"""
    items: list[SubtitleListItem]
    active_url: Optional[str] = None


class SubtitleSelectRequest(BaseModel):
    """字幕选择请求"""
    subtitle_url: str


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
