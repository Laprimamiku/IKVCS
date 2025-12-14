"""
视频统计服务

职责：播放量统计、Redis 缓存
相当于 Java 的 VideoStatsService

需求：5.5
"""
from sqlalchemy.orm import Session
from typing import Optional, Union
import logging

from app.models.video import Video
from app.repositories.video_repository import VideoRepository
# [修复 1] 导入全局单例 redis_service，而不是类 RedisService
from app.services.cache.redis_service import redis_service

logger = logging.getLogger(__name__)


class VideoStatsService:
    """视频统计服务"""
    
    @staticmethod
    def increment_view_count(db: Session, video_id: int) -> bool:
        """
        增加播放量
        """
        try:
            # 先检查视频是否存在
            video = VideoRepository.get_by_id(db, video_id)
            if not video:
                logger.warning(f"视频不存在：video_id={video_id}")
                return False
            
            # [修复 2] 直接使用单例调用，避免重复建立连接
            redis_service.increment_view_count(video_id)
            
            logger.info(f"视频 {video_id} 播放量已增加（Redis）")
            return True
        except Exception as e:
            logger.error(f"增加播放量失败：{e}")
            return False
    
    @staticmethod
    def get_merged_view_count(db: Session, video_id: int) -> int:
        """
        获取合并后的播放量（兼容旧接口）
        """
        try:
            # 从数据库获取基础播放量
            video = VideoRepository.get_by_id(db, video_id)
            if not video:
                return 0
            
            return VideoStatsService.get_view_count_from_model(video)
        except Exception as e:
            logger.error(f"获取播放量失败：{e}")
            return 0

    @staticmethod
    def get_view_count_from_model(video: Video) -> int:
        """
        [新增] 直接从视频对象获取播放量
        避免列表查询时的 N+1 数据库查询问题
        """
        try:
            db_count = video.view_count or 0
            
            # [修复 3] 使用单例获取 Redis 缓存
            redis_count = redis_service.get_view_count_from_cache(video.id)
            
            # 如果 Redis 有数据，使用 Redis 的值（因为它是最新的）
            return redis_count if redis_count is not None else db_count
        except Exception as e:
            logger.error(f"从模型获取播放量失败：{e}")
            return video.view_count or 0