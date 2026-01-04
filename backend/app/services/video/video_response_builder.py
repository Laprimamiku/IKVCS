"""
视频响应构建器

职责：组装响应数据（列表、详情）
相当于 Java 的 VideoResponseBuilder
"""
from sqlalchemy.orm import Session
from typing import Optional, TYPE_CHECKING
from math import ceil
from datetime import timezone
import logging

from app.services.video.video_query_service import VideoQueryService
from app.services.video.video_stats_service import VideoStatsService
from app.services.cache.redis_service import redis_service

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
        获取视频列表响应（包含完整的数据组装，带缓存）
        
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
        import json
        from app.schemas.video import (
            VideoListResponse,
            VideoListItemResponse,
            UploaderBriefResponse,
            CategoryBriefResponse
        )
        
        # 构建缓存键（包含所有查询参数）
        cache_key = f"video:list:page:{page}:size:{page_size}:cat:{category_id or 'all'}:kw:{keyword or 'none'}"
        
        # 尝试从缓存获取
        cached_data = redis_service.get_query_cache(cache_key)
        if cached_data:
            try:
                data = json.loads(cached_data)
                logger.debug(f"视频列表缓存命中：{cache_key}")
                return VideoListResponse(**data)
            except Exception as e:
                logger.warning(f"解析视频列表缓存失败：{e}")
        
        # 缓存未命中，从数据库查询
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
        
        response = VideoListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
        
        # 缓存响应数据（TTL: 5分钟）
        try:
            response_dict = response.model_dump()
            redis_service.set_query_cache(cache_key, json.dumps(response_dict, default=str), ttl=300)
            logger.debug(f"视频列表缓存已保存：{cache_key}")
        except Exception as e:
            logger.warning(f"保存视频列表缓存失败：{e}")
        
        return response

    @staticmethod
    def get_video_detail_response(
        db: Session,
        video_id: int
    ) -> Optional["VideoDetailResponse"]:
        """
        获取视频详情响应（包含完整的数据组装，带缓存）
        
        Args:
            db: 数据库会话
            video_id: 视频ID
            
        Returns:
            Optional[VideoDetailResponse]: 视频详情响应对象，不存在返回 None
        """
        import json
        from app.schemas.video import (
            VideoDetailResponse,
            UploaderBriefResponse,
            CategoryBriefResponse
        )
        
        # 构建缓存键
        cache_key = f"video:detail:{video_id}"
        
        # 尝试从缓存获取
        cached_data = redis_service.get_query_cache(cache_key)
        if cached_data:
            try:
                data = json.loads(cached_data)
                logger.debug(f"视频详情缓存命中：{cache_key}")
                return VideoDetailResponse(**data)
            except Exception as e:
                logger.warning(f"解析视频详情缓存失败：{e}")
        
        # 缓存未命中，从数据库查询
        video = VideoQueryService.get_video_detail(db, video_id)
        if not video:
            return None
        
        # 由于使用了 joinedload，video.uploader 和 video.category 已经预加载
        response = VideoDetailResponse(
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
        
        # 缓存响应数据（TTL: 10分钟，详情页缓存时间更长）
        try:
            response_dict = response.model_dump()
            redis_service.set_query_cache(cache_key, json.dumps(response_dict, default=str), ttl=600)
            logger.debug(f"视频详情缓存已保存：{cache_key}")
        except Exception as e:
            logger.warning(f"保存视频详情缓存失败：{e}")
        
        return response
    
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
            # 处理字幕 URL：如果 subtitle_url 为空或不是绝对路径，尝试通过 video_id 查找
            subtitle_url = video.subtitle_url
            if not subtitle_url or not subtitle_url.startswith('/'):
                # 尝试在 UPLOAD_SUBTITLE_DIR 中查找以 video_id 开头的字幕文件
                from app.core.config import settings
                from pathlib import Path
                import os
                
                subtitle_dir = Path(settings.UPLOAD_SUBTITLE_DIR)
                if subtitle_dir.exists():
                    # 查找以 video_id 开头的字幕文件
                    subtitle_files = list(subtitle_dir.glob(f"{video.id}_subtitle_*"))
                    if subtitle_files:
                        # 使用找到的第一个字幕文件
                        subtitle_file = subtitle_files[0]
                        subtitle_url = f"/uploads/subtitles/{subtitle_file.name}"
            
            items.append(
                VideoListItemResponse(
                    id=video.id,
                    title=video.title,
                    description=video.description,
                    cover_url=video.cover_url,
                    subtitle_url=subtitle_url,  # 添加字幕 URL
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
    
    @staticmethod
    def build_list_item(video, current_user_id: Optional[int] = None) -> dict:
        """
        构建单个视频列表项响应（用于观看历史等场景）
        
        Args:
            video: Video 模型对象
            current_user_id: 当前用户ID（可选，用于判断是否已点赞/收藏）
            
        Returns:
            dict: 视频列表项数据
        """
        from app.services.video.video_stats_service import VideoStatsService
        from app.services.cache.redis_service import redis_service
        
        # 判断是否已点赞（如果提供了 current_user_id）
        is_liked = False
        if current_user_id:
            # 检查 Redis 中的点赞状态
            like_key = f"likes:video:{video.id}"
            is_liked = redis_service.redis.sismember(like_key, current_user_id)
        
        return {
            "id": video.id,
            "title": video.title,
            "description": video.description,
            "cover_url": video.cover_url,
            "duration": video.duration,
            "view_count": VideoStatsService.get_view_count_from_model(video),
            "like_count": video.like_count,
            "collect_count": video.collect_count,
            "is_liked": is_liked,
            "uploader": {
                "id": video.uploader.id,
                "username": video.uploader.username,
                "nickname": video.uploader.nickname,
                "avatar": video.uploader.avatar,
            },
            "category": {
                "id": video.category.id,
                "name": video.category.name
            },
            "created_at": video.created_at.replace(tzinfo=timezone.utc).isoformat() if video.created_at.tzinfo is None else video.created_at.isoformat(),
        }
