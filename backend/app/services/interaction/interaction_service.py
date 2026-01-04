"""
互动服务层
封装点赞、收藏、举报等互动功能的业务逻辑
"""
import logging
from sqlalchemy.orm import Session
from typing import List
from fastapi import HTTPException, status

from app.repositories.interaction_repository import InteractionRepository
from app.repositories.video_repository import VideoRepository
from app.repositories.report_repository import ReportRepository
from app.core.base_service import BaseService
from app.core.error_codes import ErrorCode
from app.models.video import Video
from app.models.user import User
from app.models.interaction import UserCollection
from app.schemas.interaction import CollectionCreate, ReportCreate

logger = logging.getLogger(__name__)


class InteractionService(BaseService[Video, VideoRepository]):
    """互动服务"""
    repository = VideoRepository
    
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
        InteractionService.get_by_id_or_raise(
            db, video_id,
            resource_name="视频",
            error_code=ErrorCode.VIDEO_NOT_FOUND
        )
        
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
        
        如果举报的是视频，会将视频状态设置为审核中（status=1），并触发重新审核
        
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
        
        # 如果举报的是视频，将视频状态设置为审核中，并触发重新审核
        if report_data.target_type == "VIDEO":
            from app.models.video import Video
            from app.services.ai.video_review_service import video_review_service
            from app.repositories.upload_repository import UploadSessionRepository
            import os
            import json
            from app.core.config import settings
            from datetime import datetime
            import asyncio
            
            video = db.query(Video).filter(Video.id == report_data.target_id).first()
            if video:
                # 视频被举报后，保持原有状态（不改变 status），只在 review_report 中记录举报信息
                # 管理员可以在举报界面看到，并通过审核按钮处理
                existing_report = {}
                if video.review_report:
                    try:
                        existing_report = json.loads(video.review_report) if isinstance(video.review_report, str) else video.review_report
                    except:
                        existing_report = {}
                
                # 添加举报信息到审核报告
                if "reports" not in existing_report:
                    existing_report["reports"] = []
                
                existing_report["reports"].append({
                    "reported_by": user_id,
                    "report_reason": report_data.reason,
                    "report_description": report_data.description,
                    "report_timestamp": datetime.utcnow().isoformat()
                })
                existing_report["has_report"] = True
                existing_report["last_report_time"] = datetime.utcnow().isoformat()
                
                video.review_report = json.dumps(existing_report, ensure_ascii=False)
                db.commit()
                logger.info(f"视频被举报，已记录举报信息（保持原状态）: video_id={video.id}, reporter_id={user_id}, current_status={video.status}")
                
                # 触发重新审核（异步任务）
                try:
                    upload_session = UploadSessionRepository.get_by_video_id(db, video.id)
                    if upload_session:
                        input_path = os.path.join(
                            settings.VIDEO_ORIGINAL_DIR,
                            f"{upload_session.file_hash}_{upload_session.file_name}"
                        )
                        subtitle_path = video.subtitle_url if video.subtitle_url else None
                        if subtitle_path and not os.path.isabs(subtitle_path):
                            subtitle_path = os.path.join(settings.STORAGE_ROOT, subtitle_path.lstrip("/"))
                        
                        if os.path.exists(input_path):
                            # 在后台线程中运行异步任务
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            try:
                                loop.run_until_complete(
                                    video_review_service.review_video(
                                        video_id=video.id,
                                        video_path=input_path,
                                        subtitle_path=subtitle_path
                                    )
                                )
                            finally:
                                loop.close()
                except Exception as e:
                    logger.warning(f"触发视频重新审核失败: {e}")
