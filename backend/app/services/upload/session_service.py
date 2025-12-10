"""
会话管理服务
职责：管理上传会话的创建、查询、更新
"""
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
import logging

from app.repositories.upload_repository import UploadSessionRepository
from app.repositories.video_repository import VideoRepository
from app.models.upload import UploadSession
from app.models.video import Video
from app.schemas.upload import UploadInitRequest
from app.core.redis import get_redis

logger = logging.getLogger(__name__)


class SessionService:
    """会话管理服务"""
    
    @staticmethod
    def create_session(
        db: Session,
        user_id: int,
        upload_data: UploadInitRequest
    ) -> UploadSession:
        """
        创建新的上传会话
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            upload_data: 上传初始化数据
            
        Returns:
            UploadSession: 创建的上传会话
        """
        new_session = UploadSession(
            file_hash=upload_data.file_hash,
            user_id=user_id,
            file_name=upload_data.file_name,
            file_size=upload_data.file_size,
            total_chunks=upload_data.total_chunks,
            uploaded_chunks="",
            is_completed=False
        )
        
        db.add(new_session)
        db.commit()
        db.refresh(new_session)
        
        logger.info(f"上传会话创建成功：{new_session.file_hash}")
        return new_session
    
    @staticmethod
    def get_session_by_hash(
        db: Session,
        file_hash: str
    ) -> Optional[UploadSession]:
        """
        根据文件哈希获取上传会话
        
        Args:
            db: 数据库会话
            file_hash: 文件哈希
            
        Returns:
            Optional[UploadSession]: 上传会话，不存在返回None
        """
        return UploadSessionRepository.get_by_file_hash(db, file_hash)
    
    @staticmethod
    def check_instant_upload(
        db: Session,
        file_hash: str
    ) -> Optional[Tuple[UploadSession, Video]]:
        """
        检查是否可以秒传
        
        Args:
            db: 数据库会话
            file_hash: 文件哈希
            
        Returns:
            Optional[Tuple[UploadSession, Video]]: 如果可以秒传，返回(会话, 视频)，否则返回None
        """
        session = UploadSessionRepository.get_by_file_hash(db, file_hash)
        
        if not session or not session.is_completed or not session.video_id:
            return None
        
        # 检查视频记录及视频文件是否存在
        video = VideoRepository.get_by_id(db, session.video_id)
        if not video or not video.video_url:
            # 会话被标记完成但视频不存在或未生成可播放地址，重置会话以允许重新上传
            session.is_completed = False
            session.video_id = None
            session.uploaded_chunks = ""
            db.commit()
            return None
        
        import os
        video_path = video.video_url.lstrip("/")
        if not os.path.exists(video_path):
            # 文件不存在，重置会话
            session.is_completed = False
            session.video_id = None
            session.uploaded_chunks = ""
            db.commit()
            return None
        
        return session, video
    
    @staticmethod
    def init_redis_bitmap(file_hash: str, expire_seconds: int = 7 * 24 * 3600) -> bool:
        """
        初始化Redis BitMap
        
        Args:
            file_hash: 文件哈希
            expire_seconds: 过期时间（秒）
            
        Returns:
            bool: 是否成功
        """
        try:
            redis_client = get_redis()
            redis_key = f"upload:{file_hash}"
            
            # 如果已存在，不重复初始化
            if redis_client.exists(redis_key):
                logger.debug(f"Redis BitMap 已存在：{redis_key}")
                return True
            
            # 初始化 BitMap：设置第一个 bit 为 0（未上传）
            redis_client.setbit(redis_key, 0, 0)
            # 设置过期时间：7 天
            redis_client.expire(redis_key, expire_seconds)
            
            logger.info(f"Redis BitMap 初始化成功：{redis_key}")
            return True
        except Exception as e:
            logger.error(f"Redis 初始化失败：{e}", exc_info=True)
            return False
    
    @staticmethod
    def reset_session_for_reupload(db: Session, file_hash: str) -> bool:
        """
        当会话被标记完成但分片/视频缺失时，重置会话以允许重新上传
        """
        session = UploadSessionRepository.get_by_file_hash(db, file_hash)
        if not session:
            return False
        
        session.is_completed = False
        session.video_id = None
        session.uploaded_chunks = ""
        db.commit()
        return True
    
    @staticmethod
    def mark_session_completed(
        db: Session,
        file_hash: str,
        video_id: int
    ) -> bool:
        """
        标记会话为已完成
        
        Args:
            db: 数据库会话
            session_id: 会话ID
            video_id: 视频ID
            
        Returns:
            bool: 是否成功
        """
        return UploadSessionRepository.mark_completed(db, file_hash, video_id)

