# Pydantic 数据验证模型

# 导出通用 schemas
from .common import PageResult, ApiResponse

# 导出各功能域的 schemas
from .video import VideoListRequest, VideoUpdateRequest, VideoDetailResponse, VideoListResponse
from .user import UserRegisterRequest, UserUpdateRequest, UserResponse
from .category import CategoryCreate, CategoryResponse
from .upload import (
    UploadInitRequest, UploadInitResponse,
    UploadChunkResponse, UploadFinishRequest,
    UploadFinishResponse, UploadProgressResponse
)
from .danmaku import (
    DanmakuCreateRequest, DanmakuQueryRequest,
    DanmakuResponse, DanmakuListResponse
)
from .interaction import (
    LikeCreate, LikeStatus,
    CollectionCreate, CollectionStatus, CollectionResponse
)

__all__ = [
    # 通用
    'PageResult',
    'ApiResponse',
    # 视频
    'VideoListRequest',
    'VideoUpdateRequest',
    'VideoDetailResponse',
    'VideoListResponse',
    # 用户
    'UserRegisterRequest',
    'UserUpdateRequest',
    'UserResponse',
    # 分类
    'CategoryCreate',
    'CategoryResponse',
    # 上传
    'UploadInitRequest',
    'UploadInitResponse',
    'UploadChunkResponse',
    'UploadFinishRequest',
    'UploadFinishResponse',
    'UploadProgressResponse',
    # 弹幕
    'DanmakuCreateRequest',
    'DanmakuQueryRequest',
    'DanmakuResponse',
    'DanmakuListResponse',
    # 互动
    'LikeCreate',
    'LikeStatus',
    'CollectionCreate',
    'CollectionStatus',
    'CollectionResponse',
]
