"""
弹幕服务
职责：处理弹幕创建、查询等业务逻辑
"""
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from typing import Optional
from app.repositories.danmaku_repository import DanmakuRepository
from app.models.danmaku import Danmaku
from app.schemas.danmaku import DanmakuCreateRequest


class DanmakuService:
    """弹幕服务"""
    
    @staticmethod
    def create_danmaku(
        db: Session,
        video_id: int,
        user_id: int,
        danmaku_data: DanmakuCreateRequest
    ) -> Danmaku:
        """
        创建弹幕
        
        Args:
            db: 数据库会话
            video_id: 视频ID
            user_id: 用户ID
            danmaku_data: 弹幕数据
            
        Returns:
            Danmaku: 创建的弹幕对象
        """
        new_danmaku = Danmaku(
            video_id=video_id,
            user_id=user_id,
            content=danmaku_data.content,
            video_time=danmaku_data.video_time,
            color=danmaku_data.color,
            # 默认值，等待 AI 异步更新
            ai_score=None,
            ai_category=None
        )
        
        db.add(new_danmaku)
        db.commit()
        db.refresh(new_danmaku)
        
        return new_danmaku
    
    @staticmethod
    def get_danmaku_list(
        db: Session,
        video_id: int
    ) -> List[Danmaku]:
        """
        获取视频的弹幕列表
        
        Args:
            db: 数据库会话
            video_id: 视频ID
            
        Returns:
            List[Danmaku]: 弹幕列表
        """
        return DanmakuRepository.get_by_video_id(db, video_id)
    
    @staticmethod
    def get_danmaku_by_id(
        db: Session,
        danmaku_id: int,
        video_id: int
    ) -> Optional[Danmaku]:
        """
        根据ID和视频ID获取弹幕
        
        Args:
            db: 数据库会话
            danmaku_id: 弹幕ID
            video_id: 视频ID
            
        Returns:
            Optional[Danmaku]: 弹幕对象，不存在返回 None
        """
        danmaku = DanmakuRepository.get_by_id(db, danmaku_id)
        if danmaku and danmaku.video_id == video_id and not danmaku.is_deleted:
            return danmaku
        return None

