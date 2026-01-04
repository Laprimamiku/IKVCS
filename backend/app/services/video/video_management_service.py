"""
视频管理服务

职责：视频更新、删除
相当于 Java 的 VideoManagementService
"""
from sqlalchemy.orm import Session
from typing import Optional, TYPE_CHECKING
import logging

from app.repositories.video_repository import VideoRepository
from app.repositories.category_repository import CategoryRepository
from app.services.cache.redis_service import redis_service

if TYPE_CHECKING:
    from app.models.video import Video

logger = logging.getLogger(__name__)


class VideoManagementService:
    """视频管理服务"""
    
    @staticmethod
    def update_video(
        db: Session,
        video_id: int,
        user_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        category_id: Optional[int] = None
    ) -> Optional["Video"]:
        """
        更新视频信息
        
        Args:
            db: 数据库会话
            video_id: 视频ID
            user_id: 用户ID（用于权限验证）
            title: 视频标题（可选）
            description: 视频描述（可选）
            category_id: 分类ID（可选，None表示设置为临时分类）
            
        Returns:
            Optional[Video]: 更新后的视频对象，不存在或权限不足返回 None
        """
        from app.services.category.category_service import CategoryService
        
        video = VideoRepository.get_by_id(db, video_id)
        if not video:
            logger.warning(f"视频不存在：video_id={video_id}")
            return None
        
        # 权限验证：只有上传者可以编辑
        if video.uploader_id != user_id:
            logger.warning(f"用户 {user_id} 无权编辑视频 {video_id}（上传者：{video.uploader_id}）")
            return None
        
        # 更新字段（只更新非 None 的字段）
        update_data = {}
        if title is not None:
            update_data['title'] = title
        if description is not None:
            update_data['description'] = description
        if category_id is not None:
            if category_id == 0:
                # category_id = 0 表示设置为临时分类
                temp_category = CategoryService.get_or_create_temp_category(db)
                update_data['category_id'] = temp_category.id
            else:
                # 验证分类是否存在
                category = CategoryRepository.get_by_id(db, category_id)
                if not category:
                    logger.warning(f"分类不存在：category_id={category_id}")
                    return None
                update_data['category_id'] = category_id
        
        if update_data:
            updated_video = VideoRepository.update(db, video_id, update_data)
            logger.info(f"视频 {video_id} 信息已更新")
            # 失效相关缓存
            redis_service.invalidate_video_cache(video_id)
            logger.debug(f"视频 {video_id} 更新，已失效相关缓存")
            
            return updated_video
        
        return video
    
    @staticmethod
    def delete_video(
        db: Session,
        video_id: int,
        user_id: int,
        hard_delete: bool = False
    ) -> bool:
        """
        删除视频
        
        默认使用软删除（将 status 设置为 4），也可以选择硬删除（物理删除记录）
        
        Args:
            db: 数据库会话
            video_id: 视频ID
            user_id: 用户ID（用于权限验证）
            hard_delete: 是否硬删除（默认 False，使用软删除）
            
        Returns:
            bool: 是否删除成功
        """
        video = VideoRepository.get_by_id(db, video_id)
        if not video:
            logger.warning(f"视频不存在：video_id={video_id}")
            return False
        
        # 权限验证：只有上传者可以删除
        if video.uploader_id != user_id:
            logger.warning(f"用户 {user_id} 无权删除视频 {video_id}（上传者：{video.uploader_id}）")
            return False
        
        if hard_delete:
            # 硬删除：物理删除记录
            # 注意：这会删除关联的数据，需要谨慎使用
            success = VideoRepository.delete(db, video_id)
            if success:
                # 失效相关缓存
                redis_service.invalidate_video_cache(video_id)
                logger.info(f"视频 {video_id} 已硬删除，已失效相关缓存")
            return success
        else:
            # 软删除：将 status 设置为 4（已废弃，现在直接硬删除）
            success = VideoRepository.update(db, video_id, {'status': 4})
            if success:
                # 失效相关缓存
                redis_service.invalidate_video_cache(video_id)
                logger.info(f"视频 {video_id} 已软删除（status=4），已失效相关缓存")
            return success is not None



