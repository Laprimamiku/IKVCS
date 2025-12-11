"""
视频统计服务

职责：播放量统计、Redis 缓存
相当于 Java 的 VideoStatsService

需求：5.5
"""
from sqlalchemy.orm import Session
from typing import Optional
import logging

from app.repositories.video_repository import VideoRepository
from app.services.cache.redis_service import RedisService

logger = logging.getLogger(__name__)


class VideoStatsService:
    """视频统计服务"""
    
    @staticmethod
    def increment_view_count(db: Session, video_id: int) -> bool:
        """
        增加播放量
        
        使用 Redis Write-Back 策略：
        1. 先增加 Redis 中的计数（快速响应）
        2. 定时任务会将 Redis 数据同步到 MySQL（批量写入）
        
        Args:
            db: 数据库会话
            video_id: 视频ID
            
        Returns:
            bool: 是否成功
            
        需求：5.5（播放量统计）
        """
        try:
            # 先检查视频是否存在
            video = VideoRepository.get_by_id(db, video_id)
            if not video:
                logger.warning(f"视频不存在：video_id={video_id}")
                return False
            
            # 增加 Redis 中的播放量
            redis_service = RedisService()
            redis_service.increment_view_count(video_id)
            
            logger.info(f"视频 {video_id} 播放量已增加（Redis）")
            return True
        except Exception as e:
            logger.error(f"增加播放量失败：{e}")
            return False
    
    @staticmethod
    def get_merged_view_count(db: Session, video_id: int) -> int:
        """
        获取合并后的播放量（MySQL + Redis 增量）
        
        用于显示最新的播放量
        
        Args:
            db: 数据库会话
            video_id: 视频ID
            
        Returns:
            int: 播放量
        """
        try:
            # 从数据库获取基础播放量
            video = VideoRepository.get_by_id(db, video_id)
            if not video:
                return 0
            
            db_count = video.view_count or 0
            
            # 从 Redis 获取增量
            redis_service = RedisService()
            redis_count = redis_service.get_view_count_from_cache(video_id)
            
            # 如果 Redis 有数据，使用 Redis 的值（因为它是最新的）
            # 否则使用数据库的值
            return redis_count if redis_count is not None else db_count
        except Exception as e:
            logger.error(f"获取播放量失败：{e}")
            return 0

