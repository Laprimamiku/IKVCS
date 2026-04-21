"""
观看历史记录 Repository
"""
import logging
from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_

from app.core.repository import BaseRepository
from app.models.watch_history import WatchHistory
from app.models.video import Video
from app.services.recommendation.interest_profile_service import InterestProfileService

logger = logging.getLogger(__name__)


class WatchHistoryRepository(BaseRepository):
    """观看历史记录 Repository"""
    model = WatchHistory

    @classmethod
    def _update_interest_on_watch(cls, db: Session, user_id: int, video_id: int) -> None:
        """播放行为：按视频分类为用户兴趣加 1。"""
        category_id = db.query(Video.category_id).filter(Video.id == video_id).scalar()
        InterestProfileService.adjust_interest(db, user_id, category_id, delta=1)
    
    @classmethod
    def record_watch(
        cls,
        db: Session,
        user_id: int,
        video_id: int
    ) -> WatchHistory:
        """
        记录观看历史（如果已存在则更新观看时间）
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            video_id: 视频ID
            
        Returns:
            WatchHistory: 观看历史记录对象
        """
        # 检查是否已存在
        existing = db.query(WatchHistory).filter(
            and_(
                WatchHistory.user_id == user_id,
                WatchHistory.video_id == video_id
            )
        ).first()
        
        if existing:
            # 更新观看时间
            from datetime import datetime
            existing.watched_at = datetime.utcnow()
            try:
                cls._update_interest_on_watch(db, user_id, video_id)
            except Exception as e:
                logger.warning(f"更新用户兴趣失败（watch）：user_id={user_id}, video_id={video_id}, err={e}")
            db.commit()
            db.refresh(existing)
            return existing
        else:
            # 创建新记录
            watch_history = WatchHistory(
                user_id=user_id,
                video_id=video_id
            )
            db.add(watch_history)
            try:
                cls._update_interest_on_watch(db, user_id, video_id)
            except Exception as e:
                logger.warning(f"更新用户兴趣失败（watch）：user_id={user_id}, video_id={video_id}, err={e}")
            db.commit()
            db.refresh(watch_history)
            return watch_history
    
    @classmethod
    def get_recent_watches(
        cls,
        db: Session,
        user_id: int,
        limit: int = 3
    ) -> List[WatchHistory]:
        """
        获取用户最近的观看历史（按观看时间倒序）
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            limit: 返回数量限制（默认3）
            
        Returns:
            List[WatchHistory]: 观看历史记录列表（包含视频信息）
        """
        return db.query(WatchHistory).options(
            joinedload(WatchHistory.video).joinedload(Video.uploader),
            joinedload(WatchHistory.video).joinedload(Video.category)
        ).filter(
            WatchHistory.user_id == user_id
        ).order_by(
            WatchHistory.watched_at.desc()
        ).limit(limit).all()
    
    @classmethod
    def delete_by_user_and_video(
        cls,
        db: Session,
        user_id: int,
        video_id: int
    ) -> bool:
        """
        删除指定用户和视频的观看历史
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            video_id: 视频ID
            
        Returns:
            bool: 是否删除成功
        """
        watch_history = db.query(WatchHistory).filter(
            and_(
                WatchHistory.user_id == user_id,
                WatchHistory.video_id == video_id
            )
        ).first()
        
        if watch_history:
            db.delete(watch_history)
            db.commit()
            return True
        return False
