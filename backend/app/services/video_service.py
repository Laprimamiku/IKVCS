"""
视频业务逻辑服务

这个服务封装了视频相关的业务逻辑
相当于 Java 的 VideoService

需求：5.1-5.5
"""
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import Optional, Tuple, List
import logging

from app.models.video import Video
from app.models.user import User
from app.models.video import Category
from app.services.redis_service import RedisService

logger = logging.getLogger(__name__)


class VideoService:
    """视频服务"""
    
    @staticmethod
    def get_video_list(
        db: Session,
        page: int = 1,
        page_size: int = 20,
        category_id: Optional[int] = None,
        keyword: Optional[str] = None
    ) -> Tuple[List[Video], int]:
        """
        获取视频列表（支持分页、筛选、搜索）
        
        Args:
            db: 数据库会话
            page: 页码（从1开始）
            page_size: 每页数量
            category_id: 分类ID（可选）
            keyword: 搜索关键词（可选）
            
        Returns:
            Tuple[List[Video], int]: (视频列表, 总数)
            
        需求：
        - 5.1: 视频列表展示
        - 5.2: 按分类筛选
        - 5.3: 关键词搜索
        """
        # 基础查询：只显示已发布的视频（status=2）
        query = db.query(Video).filter(Video.status == 2)
        
        # 按分类筛选
        if category_id:
            query = query.filter(Video.category_id == category_id)
            logger.info(f"按分类筛选：category_id={category_id}")
        
        # 关键词搜索（搜索标题和描述）
        if keyword:
            search_pattern = f"%{keyword}%"
            query = query.filter(
                or_(
                    Video.title.like(search_pattern),
                    Video.description.like(search_pattern)
                )
            )
            logger.info(f"关键词搜索：keyword={keyword}")
        
        # 获取总数
        total = query.count()
        
        # 分页查询（按创建时间倒序）
        offset = (page - 1) * page_size
        videos = query.order_by(Video.created_at.desc()).offset(offset).limit(page_size).all()
        
        logger.info(f"查询视频列表：page={page}, page_size={page_size}, total={total}")
        
        return videos, total
    
    @staticmethod
    def get_video_detail(db: Session, video_id: int) -> Optional[Video]:
        """
        获取视频详情
        
        Args:
            db: 数据库会话
            video_id: 视频ID
            
        Returns:
            Optional[Video]: 视频对象，不存在返回 None
            
        需求：5.4（视频详情展示）
        """
        video = db.query(Video).filter(
            Video.id == video_id,
            Video.status == 2  # 只能查看已发布的视频
        ).first()
        
        if video:
            logger.info(f"获取视频详情：video_id={video_id}, title={video.title}")
        else:
            logger.warning(f"视频不存在或未发布：video_id={video_id}")
        
        return video
    
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
            video = db.query(Video).filter(Video.id == video_id).first()
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
            video = db.query(Video).filter(Video.id == video_id).first()
            if not video:
                return 0
            
            db_count = video.view_count
            
            # 从 Redis 获取增量
            redis_service = RedisService()
            redis_count = redis_service.get_view_count_from_cache(video_id)
            
            # 如果 Redis 有数据，使用 Redis 的值（因为它是最新的）
            # 否则使用数据库的值
            return redis_count if redis_count is not None else db_count
        except Exception as e:
            logger.error(f"获取播放量失败：{e}")
            return 0
