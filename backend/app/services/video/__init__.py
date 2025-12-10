"""
视频服务模块

将原来的 video_service.py 拆分为多个专门的服务：
- video_query_service: 视频查询、筛选、搜索
- video_stats_service: 播放量统计、Redis 缓存
- video_management_service: 视频更新、删除
- video_response_builder: 组装响应数据
"""

from app.services.video.video_query_service import VideoQueryService
from app.services.video.video_stats_service import VideoStatsService
from app.services.video.video_management_service import VideoManagementService
from app.services.video.video_response_builder import VideoResponseBuilder

__all__ = [
    "VideoQueryService",
    "VideoStatsService",
    "VideoManagementService",
    "VideoResponseBuilder",
]

