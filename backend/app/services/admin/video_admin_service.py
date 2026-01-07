"""
视频管理服务（管理员）
职责：处理管理员对视频的审核、封禁、恢复等操作
"""
import json
import logging
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session

from app.repositories.video_repository import VideoRepository
from app.models.video import Video
from app.models.user import User
from app.core.base_service import BaseService
from app.core.error_codes import ErrorCode
from app.services.cache.redis_service import redis_service
from app.utils.timezone_utils import isoformat_in_app_tz, utc_now

logger = logging.getLogger(__name__)


class VideoAdminService(BaseService[Video, VideoRepository]):
    """视频管理服务（管理员）"""
    repository = VideoRepository
    
    @staticmethod
    def approve_video(
        db: Session,
        video_id: int,
        admin: User
    ) -> dict:
        """
        管理员通过视频审核
        
        Args:
            db: 数据库会话
            video_id: 视频ID
            admin: 管理员用户对象
            
        Returns:
            dict: 包含状态消息的字典
            
        Raises:
            ResourceNotFoundException: 视频不存在
        """
        video = VideoAdminService.get_by_id_or_raise(
            db, video_id,
            resource_name="视频",
            error_code=ErrorCode.VIDEO_NOT_FOUND
        )
        
        # 记录原始状态
        original_status = video.status
        
        # 如果原本是已发布状态，保持已发布；否则设置为已发布
        if original_status == 2:
            # 保持已发布状态，不改变
            video.status = 2
            status_message = "视频已通过审核（保持已发布状态）"
        else:
            # 设置为已发布
            video.status = 2
            status_message = "视频已通过审核"
        
        video.review_status = 1  # 审核通过
        
        # 更新审核报告，记录管理员操作
        review_report = {
            "message": "管理员审核通过",
            "timestamp": isoformat_in_app_tz(utc_now()),
            "admin_id": admin.id,
            "admin_username": admin.username,
            "original_status": original_status,
            "final_status": video.status
        }
        
        if video.review_report:
            try:
                existing_report = json.loads(video.review_report) if isinstance(video.review_report, str) else video.review_report
                review_report.update(existing_report)
                # 清除举报标记（如果存在）
                if "has_report" in review_report:
                    review_report["has_report"] = False
            except Exception as e:
                logger.warning(f"解析审核报告失败: {e}")
        
        video.review_report = json.dumps(review_report, ensure_ascii=False)
        db.commit()
        
        # 失效相关缓存
        redis_service.invalidate_video_cache(video_id)
        logger.info(
            f"管理员 {admin.username} 通过视频审核: video_id={video_id}, "
            f"original_status={original_status}, final_status={video.status}，已失效相关缓存"
        )
        
        return {"message": status_message}
    
    @staticmethod
    def reject_video(
        db: Session,
        video_id: int,
        admin: User
    ) -> dict:
        """
        管理员拒绝视频审核
        
        Args:
            db: 数据库会话
            video_id: 视频ID
            admin: 管理员用户对象
            
        Returns:
            dict: 包含状态消息的字典
            
        Raises:
            ResourceNotFoundException: 视频不存在
        """
        video = VideoAdminService.get_by_id_or_raise(
            db, video_id,
            resource_name="视频",
            error_code=ErrorCode.VIDEO_NOT_FOUND
        )
        
        video.status = 3  # 拒绝 / 封禁
        video.review_status = 2  # 审核拒绝
        
        # 更新审核报告，记录管理员操作
        review_report = {
            "message": "管理员审核拒绝",
            "timestamp": isoformat_in_app_tz(utc_now()),
            "admin_id": admin.id,
            "admin_username": admin.username
        }
        
        if video.review_report:
            try:
                existing_report = json.loads(video.review_report) if isinstance(video.review_report, str) else video.review_report
                review_report.update(existing_report)
            except Exception as e:
                logger.warning(f"解析审核报告失败: {e}")
        
        video.review_report = json.dumps(review_report, ensure_ascii=False)
        db.commit()
        
        # 失效相关缓存
        redis_service.invalidate_video_cache(video_id)
        logger.info(
            f"管理员 {admin.username} 拒绝视频审核: video_id={video_id}，已失效相关缓存"
        )
        
        return {"message": "视频已被拒绝"}
    
    @staticmethod
    def ban_video(
        db: Session,
        video_id: int
    ) -> dict:
        """
        封禁视频
        
        Args:
            db: 数据库会话
            video_id: 视频ID
            
        Returns:
            dict: 包含状态消息的字典
            
        Raises:
            ResourceNotFoundException: 视频不存在
        """
        video = VideoAdminService.get_by_id_or_raise(
            db, video_id,
            resource_name="视频",
            error_code=ErrorCode.VIDEO_NOT_FOUND
        )
        
        video.status = 3
        db.commit()
        
        # 失效相关缓存
        redis_service.invalidate_video_cache(video_id)
        
        return {"message": "视频已封禁"}
    
    @staticmethod
    def restore_video(
        db: Session,
        video_id: int
    ) -> dict:
        """
        恢复视频发布
        
        Args:
            db: 数据库会话
            video_id: 视频ID
            
        Returns:
            dict: 包含状态消息的字典
            
        Raises:
            ResourceNotFoundException: 视频不存在
        """
        video = VideoAdminService.get_by_id_or_raise(
            db, video_id,
            resource_name="视频",
            error_code=ErrorCode.VIDEO_NOT_FOUND
        )
        
        video.status = 2
        db.commit()
        
        # 失效相关缓存
        redis_service.invalidate_video_cache(video_id)
        
        return {"message": "视频已恢复发布"}
