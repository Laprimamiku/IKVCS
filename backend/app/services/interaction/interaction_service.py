"""
互动服务层
封装点赞、收藏、举报等互动功能的业务逻辑
"""
from sqlalchemy.orm import Session
from typing import List
from fastapi import HTTPException, status

from app.repositories.interaction_repository import InteractionRepository
from app.repositories.video_repository import VideoRepository
from app.repositories.report_repository import ReportRepository
from app.models.user import User
from app.models.interaction import UserCollection
from app.schemas.interaction import CollectionCreate, ReportCreate
from app.core.exceptions import ResourceNotFoundException


class InteractionService:
    """互动服务"""
    
    @staticmethod
    def collect_video(
        db: Session,
        user_id: int,
        video_id: int
    ) -> dict:
        """
        收藏视频
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            video_id: 视频ID
            
        Returns:
            dict: 包含 is_collected 的状态
        """
        # 检查视频是否存在
        video = VideoRepository.get_by_id(db, video_id)
        if not video:
            raise ResourceNotFoundException(resource="视频", resource_id=video_id)
        
        # 检查是否已收藏
        exists = InteractionRepository.get_collection(
            db, user_id, video_id
        )
        
        if exists:
            return {"is_collected": True}
        
        # 创建收藏记录
        InteractionRepository.create_collection(db, user_id, video_id)
        
        # 同步增加视频收藏数
        VideoRepository.increment_collect_count(db, video_id)
        
        return {"is_collected": True}
    
    @staticmethod
    def uncollect_video(
        db: Session,
        user_id: int,
        video_id: int
    ) -> dict:
        """
        取消收藏视频
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            video_id: 视频ID
            
        Returns:
            dict: 包含 is_collected 的状态
        """
        # 查找收藏记录
        collection = InteractionRepository.get_collection(
            db, user_id, video_id
        )
        
        if collection:
            # 删除收藏记录
            InteractionRepository.delete_collection(db, collection.id)
            
            # 同步减少视频收藏数
            VideoRepository.decrement_collect_count(db, video_id)
        
        return {"is_collected": False}
    
    @staticmethod
    def get_user_collections(
        db: Session,
        user_id: int,
        page: int = 1,
        page_size: int = 20
    ) -> List[UserCollection]:
        """
        获取用户的收藏列表
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            page: 页码
            page_size: 每页数量
            
        Returns:
            List[UserCollection]: 收藏列表
        """
        skip = (page - 1) * page_size
        return InteractionRepository.get_user_collections(
            db, user_id, skip=skip, limit=page_size
        )
    
    @staticmethod
    def create_report(
        db: Session,
        user_id: int,
        report_data: ReportCreate
    ) -> None:
        """
        创建举报记录
        
        Args:
            db: 数据库会话
            user_id: 举报用户ID
            report_data: 举报数据
            
        Raises:
            HTTPException: 重复举报
        """
        # 检查是否重复举报
        if ReportRepository.exists(db, user_id, report_data.target_type, report_data.target_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="您已经举报过该内容，请耐心等待管理员处理"
            )
        
        # 创建举报记录
        ReportRepository.create(db, report_data, user_id)
