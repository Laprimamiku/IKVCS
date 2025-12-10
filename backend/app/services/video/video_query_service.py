"""
视频查询服务

职责：视频查询、筛选、搜索
相当于 Java 的 VideoQueryService

需求：5.1-5.3
"""
from sqlalchemy.orm import Session
from typing import Optional, Tuple, List
import logging

from app.repositories.video_repository import VideoRepository

logger = logging.getLogger(__name__)


class VideoQueryService:
    """视频查询服务"""
    
    @staticmethod
    def get_video_list(
        db: Session,
        page: int = 1,
        page_size: int = 20,
        category_id: Optional[int] = None,
        keyword: Optional[str] = None
    ) -> Tuple[List, int]:
        """
        获取视频列表（支持分页、筛选、搜索）
        
        使用 Repository 层访问数据
        
        Args:
            db: 数据库会话
            page: 页码（从1开始）
            page_size: 每页数量
            category_id: 分类ID（可选）
            keyword: 搜索关键词（可选）
            
        Returns:
            Tuple[List[Video], int]: (视频列表, 总数)
        """
        return VideoRepository.get_published_list(
            db=db,
            page=page,
            page_size=page_size,
            category_id=category_id,
            keyword=keyword
        )
    
    @staticmethod
    def get_video_detail(db: Session, video_id: int):
        """
        获取视频详情
        
        使用 Repository 层访问数据
        
        Args:
            db: 数据库会话
            video_id: 视频ID
            
        Returns:
            Optional[Video]: 视频对象，不存在返回 None
        """
        video = VideoRepository.get_by_id_with_relations(db, video_id)
        
        if video:
            logger.info(f"获取视频详情：video_id={video_id}, title={video.title}")
        else:
            logger.warning(f"视频不存在：video_id={video_id}")
        return video
    
    @staticmethod
    def get_user_video_list(
        db: Session,
        user_id: int,
        page: int = 1,
        page_size: int = 20,
        status: Optional[int] = None
    ) -> Tuple[List, int]:
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
        result = VideoRepository.get_user_video_list(
            db=db,
            user_id=user_id,
            page=page,
            page_size=page_size,
            status=status
        )
        
        logger.info(f"查询用户 {user_id} 的视频列表：page={page}, page_size={page_size}, total={result[1]}")
        
        return result

