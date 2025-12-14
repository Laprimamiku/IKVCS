"""
视频响应构建器

职责：组装响应数据（列表、详情）
相当于 Java 的 VideoResponseBuilder
"""
from sqlalchemy.orm import Session
from typing import Optional, TYPE_CHECKING
from math import ceil
import logging

from app.services.video.video_query_service import VideoQueryService
from app.services.video.video_stats_service import VideoStatsService

# 类型检查时导入，避免循环导入
if TYPE_CHECKING:
    from app.schemas.video import VideoListResponse, VideoDetailResponse

logger = logging.getLogger(__name__)


class VideoResponseBuilder:
    """视频响应构建器"""
    
    @staticmethod
    def get_video_list_response(
        db: Session,
        page: int = 1,
        page_size: int = 20,
        category_id: Optional[int] = None,
        keyword: Optional[str] = None
    ) -> "VideoListResponse":
        """
        获取视频列表响应（包含完整的数据组装）
        
        这个方法封装了数据查询、组装、分页计算等所有业务逻辑
        路由层只需要调用此方法即可
        
        Args:
            db: 数据库会话
            page: 页码（从1开始）
            page_size: 每页数量
            category_id: 分类ID（可选）
            keyword: 搜索关键词（可选）
            
        Returns:
            VideoListResponse: 视频列表响应对象
        """
        from app.schemas.video import (
            VideoListResponse,
            VideoListItemResponse,
            UploaderBriefResponse,
            CategoryBriefResponse
        )
        
        # 获取视频列表和总数
        videos, total = VideoQueryService.get_video_list(
            db=db,
            page=page,
            page_size=page_size,
            category_id=category_id,
            keyword=keyword,
        )
        
        # 计算总页数
        total_pages = ceil(total / page_size) if total > 0 else 0
        
        # 组装响应数据
        items = []
        for video in videos:
            # 由于使用了 joinedload，video.uploader 和 video.category 已经预加载
            items.append(
                VideoListItemResponse(
                    id=video.id,
                    title=video.title,
                    description=video.description,
                    cover_url=video.cover_url,
                    duration=video.duration,
                    # 直接传入 video 对象，省去一次数据库查询
view_count=VideoStatsService.get_view_count_from_model(video),
                    like_count=video.like_count,
                    collect_count=video.collect_count,
                    uploader=UploaderBriefResponse(
                        id=video.uploader.id,
                        username=video.uploader.username,
                        nickname=video.uploader.nickname,
                        avatar=video.uploader.avatar,
                    ),
                    category=CategoryBriefResponse(
                        id=video.category.id,
                        name=video.category.name
                    ),
                    created_at=video.created_at,
                )
            )
        
        return VideoListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    @staticmethod
    def get_video_detail_response(
        db: Session,
        video_id: int
    ) -> Optional["VideoDetailResponse"]:
        """
        获取视频详情响应（包含完整的数据组装）
        
        Args:
            db: 数据库会话
            video_id: 视频ID
            
        Returns:
            Optional[VideoDetailResponse]: 视频详情响应对象，不存在返回 None
        """
        from app.schemas.video import (
            VideoDetailResponse,
            UploaderBriefResponse,
            CategoryBriefResponse
        )
        
        video = VideoQueryService.get_video_detail(db, video_id)
        if not video:
            return None
        
        # 由于使用了 joinedload，video.uploader 和 video.category 已经预加载
        return VideoDetailResponse(
            id=video.id,
            title=video.title,
            description=video.description,
            cover_url=video.cover_url,
            video_url=video.video_url,
            subtitle_url=video.subtitle_url,
            duration=video.duration,
            status=video.status,
            view_count=VideoStatsService.get_merged_view_count(db, video.id),
            like_count=video.like_count,
            collect_count=video.collect_count,
            uploader=UploaderBriefResponse(
                id=video.uploader.id,
                username=video.uploader.username,
                nickname=video.uploader.nickname,
                avatar=video.uploader.avatar,
            ),
            category=CategoryBriefResponse(
                id=video.category.id,
                name=video.category.name
            ),
            created_at=video.created_at,
        )
    
    @staticmethod
    def get_user_video_list_response(
        db: Session,
        user_id: int,
        page: int = 1,
        page_size: int = 20,
        status: Optional[int] = None
    ) -> "VideoListResponse":
        """
        获取用户上传的视频列表响应（包含完整的数据组装）
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            page: 页码（从1开始）
            page_size: 每页数量
            status: 视频状态筛选（可选）
            
        Returns:
            VideoListResponse: 视频列表响应对象
        """
        from app.schemas.video import (
            VideoListResponse,
            VideoListItemResponse,
            UploaderBriefResponse,
            CategoryBriefResponse
        )
        
        # 获取视频列表和总数
        videos, total = VideoQueryService.get_user_video_list(
            db=db,
            user_id=user_id,
            page=page,
            page_size=page_size,
            status=status,
        )
        
        # 计算总页数
        total_pages = ceil(total / page_size) if total > 0 else 0
        
        # 组装响应数据
        items = []
        for video in videos:
            items.append(
                VideoListItemResponse(
                    id=video.id,
                    title=video.title,
                    description=video.description,
                    cover_url=video.cover_url,
                    duration=video.duration,
                    view_count=VideoStatsService.get_merged_view_count(db, video.id),
                    like_count=video.like_count,
                    collect_count=video.collect_count,
                    uploader=UploaderBriefResponse(
                        id=video.uploader.id,
                        username=video.uploader.username,
                        nickname=video.uploader.nickname,
                        avatar=video.uploader.avatar,
                    ),
                    category=CategoryBriefResponse(
                        id=video.category.id,
                        name=video.category.name
                    ),
                    created_at=video.created_at,
                )
            )
        
        return VideoListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

