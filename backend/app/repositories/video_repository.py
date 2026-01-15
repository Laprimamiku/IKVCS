"""
视频 Repository
提供视频相关的数据访问方法
"""
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_

from app.core.repository import BaseRepository
from app.core.video_constants import VideoStatus
from app.models.video import Video, Category


class VideoRepository(BaseRepository):
    """视频 Repository"""
    model = Video
    
    @classmethod
    def get_by_id_with_relations(
        cls,
        db: Session,
        video_id: int
    ) -> Optional[Video]:
        """
        根据ID查询视频（包含关联数据）
        
        Args:
            db: 数据库会话
            video_id: 视频ID
            
        Returns:
            Optional[Video]: 视频对象，不存在返回None
        """
        return db.query(Video).options(
            joinedload(Video.uploader),
            joinedload(Video.category)
        ).filter(Video.id == video_id).first()
    
    @classmethod
    def get_published_list(
        cls,
        db: Session,
        page: int = 1,
        page_size: int = 20,
        category_id: Optional[int] = None,
        keyword: Optional[str] = None
    ) -> Tuple[List[Video], int]:
        """
        获取已发布的视频列表（支持分页、筛选、搜索）
        
        Args:
            db: 数据库会话
            page: 页码（从1开始）
            page_size: 每页数量
            category_id: 分类ID（可选）
            keyword: 搜索关键词（可选）
            
        Returns:
            Tuple[List[Video], int]: (视频列表, 总数)
        """
        # 基础查询：只显示已发布的视频
        query = db.query(Video).options(
            joinedload(Video.uploader),
            joinedload(Video.category)
        ).filter(Video.status == VideoStatus.PUBLISHED)
        
        # 按分类筛选
        if category_id:
            query = query.filter(Video.category_id == category_id)
        
        # 关键词搜索（搜索标题和描述）
        if keyword:
            keyword_pattern = f"%{keyword}%"
            query = query.filter(
                or_(
                    Video.title.like(keyword_pattern),
                    Video.description.like(keyword_pattern)
                )
            )
        
        # 优化：先分页查询，再获取总数（如果数据量大，可以进一步优化为缓存总数）
        offset = (page - 1) * page_size
        videos = query.order_by(Video.created_at.desc()).offset(offset).limit(page_size).all()
        
        # 获取总数（使用独立的查询，避免影响分页查询的性能）
        # 优化：对于总数查询，不需要加载关联数据，使用更轻量的查询
        # 优化：尝试从缓存获取总数
        from app.services.cache.redis_service import redis_service
        count_cache_key = f"video:count:status:{VideoStatus.PUBLISHED}:cat:{category_id or 'all'}:kw:{keyword or 'none'}"
        total = redis_service.get_count_cache(count_cache_key)
        
        if total is None:
            # 缓存未命中，从数据库查询
            count_query = db.query(Video).filter(Video.status == VideoStatus.PUBLISHED)
            if category_id:
                count_query = count_query.filter(Video.category_id == category_id)
            if keyword:
                keyword_pattern = f"%{keyword}%"
                count_query = count_query.filter(
                    or_(
                        Video.title.like(keyword_pattern),
                        Video.description.like(keyword_pattern)
                    )
                )
            total = count_query.count()
            # 缓存总数（TTL: 5分钟）
            redis_service.set_count_cache(count_cache_key, total, ttl=300)
        
        return videos, total
    
    @classmethod
    def get_user_video_list(
        cls,
        db: Session,
        user_id: int,
        page: int = 1,
        page_size: int = 20,
        status: Optional[int] = None
    ) -> Tuple[List[Video], int]:
        """
        获取用户上传的视频列表
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            page: 页码（从1开始）
            page_size: 每页数量
            status: 视频状态筛选（可选）
            
        Returns:
            Tuple[List[Video], int]: (视频列表, 总数)
        """
        # 基础查询：用户上传的视频
        query = db.query(Video).options(
            joinedload(Video.uploader),
            joinedload(Video.category)
        ).filter(Video.uploader_id == user_id)
        
        # 按状态筛选
        if status is not None:
            query = query.filter(Video.status == status)
        
        # 获取总数
        total_query = db.query(Video).filter(Video.uploader_id == user_id)
        if status is not None:
            total_query = total_query.filter(Video.status == status)
        total = total_query.count()
        
        # 分页查询（按创建时间倒序）
        offset = (page - 1) * page_size
        videos = query.order_by(Video.created_at.desc()).offset(offset).limit(page_size).all()
        
        return videos, total
    
    @classmethod
    def get_by_file_hash(
        cls,
        db: Session,
        file_hash: str
    ) -> Optional[Video]:
        """
        根据文件哈希查询视频（用于秒传检测）
        
        Args:
            db: 数据库会话
            file_hash: 文件哈希
            
        Returns:
            Optional[Video]: 视频对象，不存在返回None
        """
        # 通过UploadSession关联查询
        from app.models.upload import UploadSession
        session = db.query(UploadSession).filter(
            UploadSession.file_hash == file_hash,
            UploadSession.is_completed == True,
            UploadSession.video_id.isnot(None)
        ).first()
        
        if session and session.video_id:
            return cls.get_by_id_with_relations(db, session.video_id)
        
        return None
    
    @classmethod
    def increment_view_count(
        cls,
        db: Session,
        video_id: int
    ) -> bool:
        """
        增加视频播放量
        
        Args:
            db: 数据库会话
            video_id: 视频ID
            
        Returns:
            bool: 是否成功
        """
        video = cls.get_by_id(db, video_id)
        if not video:
            return False
        
        video.view_count = (video.view_count or 0) + 1
        db.commit()
        return True
    
    @classmethod
    def increment_collect_count(
        cls,
        db: Session,
        video_id: int
    ) -> bool:
        """
        增加视频收藏数
        
        Args:
            db: 数据库会话
            video_id: 视频ID
            
        Returns:
            bool: 是否成功
        """
        video = cls.get_by_id(db, video_id)
        if not video:
            return False
        
        video.collect_count = (video.collect_count or 0) + 1
        db.commit()
        return True
    
    @classmethod
    def decrement_collect_count(
        cls,
        db: Session,
        video_id: int
    ) -> bool:
        """
        减少视频收藏数
        
        Args:
            db: 数据库会话
            video_id: 视频ID
            
        Returns:
            bool: 是否成功
        """
        video = cls.get_by_id(db, video_id)
        if not video:
            return False
        
        if video.collect_count and video.collect_count > 0:
            video.collect_count = video.collect_count - 1
        else:
            video.collect_count = 0
        db.commit()
        return True

