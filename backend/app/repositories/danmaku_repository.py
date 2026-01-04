"""
弹幕 Repository
提供弹幕相关的数据访问方法
"""
from typing import Optional, List
from sqlalchemy.orm import Session, joinedload

from app.core.repository import BaseRepository
from app.models.danmaku import Danmaku


class DanmakuRepository(BaseRepository):
    """弹幕 Repository"""
    model = Danmaku
    
    @classmethod
    def get_by_video_id(
        cls,
        db: Session,
        video_id: int
    ) -> List[Danmaku]:
        """
        根据视频ID查询弹幕列表（包含用户信息）
        
        Args:
            db: 数据库会话
            video_id: 视频ID
            
        Returns:
            List[Danmaku]: 弹幕列表
        """
        return db.query(Danmaku).options(
            joinedload(Danmaku.user)
        ).filter(
            Danmaku.video_id == video_id,
            Danmaku.is_deleted == False
        ).order_by(Danmaku.video_time).all()
    
    @classmethod
    def get_by_video_id_and_time_range(
        cls,
        db: Session,
        video_id: int,
        start_time: float,
        end_time: float
    ) -> List[Danmaku]:
        """
        根据视频ID和时间范围查询弹幕
        
        Args:
            db: 数据库会话
            video_id: 视频ID
            start_time: 开始时间（秒）
            end_time: 结束时间（秒）
            
        Returns:
            List[Danmaku]: 弹幕列表
        """
        return db.query(Danmaku).filter(
            Danmaku.video_id == video_id,
            Danmaku.video_time >= start_time,
            Danmaku.video_time <= end_time,
            Danmaku.is_deleted == False
        ).order_by(Danmaku.video_time).all()

