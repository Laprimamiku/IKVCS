"""
视频状态服务
职责：处理视频状态查询和转码触发等业务逻辑
"""
from sqlalchemy.orm import Session
from typing import Optional

from app.repositories.video_repository import VideoRepository
from app.repositories.upload_repository import UploadSessionRepository
from app.core.base_service import BaseService
from app.core.exceptions import ValidationException
from app.core.error_codes import ErrorCode
from app.models.video import Video
from app.models.upload import UploadSession


class VideoStatusService(BaseService[Video, VideoRepository]):
    """视频状态服务"""
    repository = VideoRepository
    
    @staticmethod
    def get_video_status(db: Session, video_id: int) -> dict:
        """
        获取视频状态信息
        
        Args:
            db: 数据库会话
            video_id: 视频ID
            
        Returns:
            dict: 视频状态信息
            
        Raises:
            ResourceNotFoundException: 视频不存在
        """
        video = VideoStatusService.get_by_id_or_raise(
            db, video_id,
            resource_name="视频",
            error_code=ErrorCode.VIDEO_NOT_FOUND
        )
        
        status_map = {0: "转码中", 1: "审核中", 2: "已发布", 3: "已拒绝", -1: "转码失败"}
        
        return {
            "video_id": video.id,
            "title": video.title,
            "status": video.status,
            "status_text": status_map.get(video.status, "未知状态"),
            "video_url": video.video_url,
            "duration": video.duration,
        }
    
    @staticmethod
    def trigger_transcode(db: Session, video_id: int) -> dict:
        """
        触发视频转码
        
        Args:
            db: 数据库会话
            video_id: 视频ID
            
        Returns:
            dict: 转码任务信息
            
        Raises:
            ResourceNotFoundException: 视频不存在
            ValidationException: 没有对应的上传会话
        """
        video = VideoStatusService.get_by_id_or_raise(
            db, video_id,
            resource_name="视频",
            error_code=ErrorCode.VIDEO_NOT_FOUND
        )
        
        upload_session = UploadSessionRepository.get_by_video_id(db, video_id)
        if not upload_session:
            raise ValidationException(message="没有对应的上传会话，无法转码")
        
        # 更新视频状态为转码中
        video.status = 0
        db.commit()
        
        return {
            "message": "转码任务已启动，请稍后查询视频状态",
            "video_id": video_id,
            "status": "transcoding"
        }




















