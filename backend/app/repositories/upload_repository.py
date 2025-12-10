"""
上传会话 Repository
提供上传会话相关的数据访问方法
"""
from typing import Optional, List
from sqlalchemy.orm import Session

from app.core.repository import BaseRepository
from app.models.upload import UploadSession


class UploadSessionRepository(BaseRepository):
    """上传会话 Repository"""
    model = UploadSession
    
    @classmethod
    def get_by_file_hash(
        cls,
        db: Session,
        file_hash: str
    ) -> Optional[UploadSession]:
        """
        根据文件哈希查询上传会话
        
        Args:
            db: 数据库会话
            file_hash: 文件哈希
            
        Returns:
            Optional[UploadSession]: 上传会话对象，不存在返回None
        """
        return db.query(UploadSession).filter(
            UploadSession.file_hash == file_hash
        ).first()
    
    @classmethod
    def get_user_sessions(
        cls,
        db: Session,
        user_id: int,
        limit: int = 10
    ) -> List[UploadSession]:
        """
        获取用户的上传会话列表
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            limit: 限制数量
            
        Returns:
            List[UploadSession]: 上传会话列表
        """
        return db.query(UploadSession).filter(
            UploadSession.user_id == user_id
        ).order_by(UploadSession.created_at.desc()).limit(limit).all()
    
    @classmethod
    def mark_completed(
        cls,
        db: Session,
        file_hash: str,
        video_id: int
    ) -> bool:
        """
        标记上传会话为已完成
        
        Args:
            db: 数据库会话
            session_id: 会话ID
            video_id: 视频ID
            
        Returns:
            bool: 是否成功
        """
        session = cls.get_by_file_hash(db, file_hash)
        if not session:
            return False
        
        session.is_completed = True
        session.video_id = video_id
        db.commit()
        return True
    
    @classmethod
    def get_by_video_id(
        cls,
        db: Session,
        video_id: int
    ) -> Optional[UploadSession]:
        """
        根据视频ID查询上传会话
        
        Args:
            db: 数据库会话
            video_id: 视频ID
            
        Returns:
            Optional[UploadSession]: 上传会话对象，不存在返回None
        """
        return db.query(UploadSession).filter(
            UploadSession.video_id == video_id
        ).first()

