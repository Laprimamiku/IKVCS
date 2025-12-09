"""
视频业务逻辑服务

这个服务封装了视频相关的业务逻辑
相当于 Java 的 VideoService

需求：5.1-5.5
"""
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import Optional, Tuple, List, TYPE_CHECKING
import logging
import os

from app.models.video import Video
from app.models.user import User
from app.models.video import Category
from app.services.redis_service import RedisService

# 类型检查时导入，避免循环导入
if TYPE_CHECKING:
    from app.schemas.video import VideoListResponse, VideoDetailResponse

logger = logging.getLogger(__name__)


class VideoService:
    """视频服务"""
    
    @staticmethod
    def get_video_list(
        db: Session,
        page: int = 1,
        page_size: int = 20,
        category_id: Optional[int] = None,
        keyword: Optional[str] = None
    ) -> Tuple[List[Video], int]:
        """
        获取视频列表（支持分页、筛选、搜索）
        
        使用 joinedload 预加载关联数据，避免 N+1 查询问题
        
        Args:
            db: 数据库会话
            page: 页码（从1开始）
            page_size: 每页数量
            category_id: 分类ID（可选）
            keyword: 搜索关键词（可选）
            
        Returns:
            Tuple[List[Video], int]: (视频列表, 总数)
            
        需求：
        - 5.1: 视频列表展示
        - 5.2: 按分类筛选
        - 5.3: 关键词搜索
        """
        from sqlalchemy.orm import joinedload
        
        # 基础查询：只显示已发布的视频（status=2）
        # 使用 joinedload 预加载 uploader 和 category，避免 N+1 查询
        query = db.query(Video).options(
            joinedload(Video.uploader),
            joinedload(Video.category)
        ).filter(Video.status == 2)
        
        # 按分类筛选
        if category_id:
            query = query.filter(Video.category_id == category_id)
            logger.info(f"按分类筛选：category_id={category_id}")
        
        # 关键词搜索（搜索标题和描述）
        if keyword:
            search_pattern = f"%{keyword}%"
            query = query.filter(
                or_(
                    Video.title.like(search_pattern),
                    Video.description.like(search_pattern)
                )
            )
            logger.info(f"关键词搜索：keyword={keyword}")
        
        # 获取总数（需要先去除 joinedload，避免影响 count）
        total_query = db.query(Video).filter(Video.status == 2)
        if category_id:
            total_query = total_query.filter(Video.category_id == category_id)
        if keyword:
            search_pattern = f"%{keyword}%"
            total_query = total_query.filter(
                or_(
                    Video.title.like(search_pattern),
                    Video.description.like(search_pattern)
                )
            )
        total = total_query.count()
        
        # 分页查询（按创建时间倒序）
        offset = (page - 1) * page_size
        videos = query.order_by(Video.created_at.desc()).offset(offset).limit(page_size).all()
        
        logger.info(f"查询视频列表：page={page}, page_size={page_size}, total={total}")
        
        return videos, total
    
    @staticmethod
    def get_video_detail(db: Session, video_id: int) -> Optional[Video]:
        """
        获取视频详情
        
        使用 joinedload 预加载关联数据，避免 N+1 查询问题
        
        Args:
            db: 数据库会话
            video_id: 视频ID
            
        Returns:
            Optional[Video]: 视频对象，不存在返回 None
            
        需求：5.4（视频详情展示）
        """
        from sqlalchemy.orm import joinedload
        
        video = db.query(Video).options(
            joinedload(Video.uploader),
            joinedload(Video.category)
        ).filter(Video.id == video_id).first()
    
        if video:
            logger.info(f"获取视频详情：video_id={video_id}, title={video.title}")
        else:
            logger.warning(f"视频不存在：video_id={video_id}")
        return video
    
    @staticmethod
    def increment_view_count(db: Session, video_id: int) -> bool:
        """
        增加播放量
        
        使用 Redis Write-Back 策略：
        1. 先增加 Redis 中的计数（快速响应）
        2. 定时任务会将 Redis 数据同步到 MySQL（批量写入）
        
        Args:
            db: 数据库会话
            video_id: 视频ID
            
        Returns:
            bool: 是否成功
            
        需求：5.5（播放量统计）
        """
        try:
            # 先检查视频是否存在
            video = db.query(Video).filter(Video.id == video_id).first()
            if not video:
                logger.warning(f"视频不存在：video_id={video_id}")
                return False
            
            # 增加 Redis 中的播放量
            redis_service = RedisService()
            redis_service.increment_view_count(video_id)
            
            logger.info(f"视频 {video_id} 播放量已增加（Redis）")
            return True
        except Exception as e:
            logger.error(f"增加播放量失败：{e}")
            return False
    
    @staticmethod
    def get_merged_view_count(db: Session, video_id: int) -> int:
        """
        获取合并后的播放量（MySQL + Redis 增量）
        
        用于显示最新的播放量
        
        Args:
            db: 数据库会话
            video_id: 视频ID
            
        Returns:
            int: 播放量
        """
        try:
            # 从数据库获取基础播放量
            video = db.query(Video).filter(Video.id == video_id).first()
            if not video:
                return 0
            
            db_count = video.view_count
            
            # 从 Redis 获取增量
            redis_service = RedisService()
            redis_count = redis_service.get_view_count_from_cache(video_id)
            
            # 如果 Redis 有数据，使用 Redis 的值（因为它是最新的）
            # 否则使用数据库的值
            return redis_count if redis_count is not None else db_count
        except Exception as e:
            logger.error(f"获取播放量失败：{e}")
            return 0
    
    @staticmethod
    def get_video_list_response(
        db: Session,
        page: int = 1,
        page_size: int = 20,
        category_id: Optional[int] = None,
        keyword: Optional[str] = None
    ) -> "VideoListResponse":
        """
        获取视频列表响应（包含完整的数据组装）
        
        这个方法封装了数据查询、组装、分页计算等所有业务逻辑
        路由层只需要调用此方法即可
        
        Args:
            db: 数据库会话
            page: 页码（从1开始）
            page_size: 每页数量
            category_id: 分类ID（可选）
            keyword: 搜索关键词（可选）
            
        Returns:
            VideoListResponse: 视频列表响应对象
        """
        from math import ceil
        from app.schemas.video import (
            VideoListResponse,
            VideoListItemResponse,
            UploaderBriefResponse,
            CategoryBriefResponse
        )
        
        # 获取视频列表和总数
        videos, total = VideoService.get_video_list(
            db=db,
            page=page,
            page_size=page_size,
            category_id=category_id,
            keyword=keyword,
        )
        
        # 计算总页数
        total_pages = ceil(total / page_size) if total > 0 else 0
        
        # 组装响应数据
        items = []
        for video in videos:
            # 由于使用了 joinedload，video.uploader 和 video.category 已经预加载
            items.append(
                VideoListItemResponse(
                    id=video.id,
                    title=video.title,
                    description=video.description,
                    cover_url=video.cover_url,
                    duration=video.duration,
                    view_count=VideoService.get_merged_view_count(db, video.id),
                    like_count=video.like_count,
                    collect_count=video.collect_count,
                    uploader=UploaderBriefResponse(
                        id=video.uploader.id,
                        username=video.uploader.username,
                        nickname=video.uploader.nickname,
                        avatar=video.uploader.avatar,
                    ),
                    category=CategoryBriefResponse(
                        id=video.category.id,
                        name=video.category.name
                    ),
                    created_at=video.created_at,
                )
            )
        
        return VideoListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    @staticmethod
    def get_video_detail_response(
        db: Session,
        video_id: int
    ) -> Optional["VideoDetailResponse"]:
        """
        获取视频详情响应（包含完整的数据组装）
        
        Args:
            db: 数据库会话
            video_id: 视频ID
            
        Returns:
            Optional[VideoDetailResponse]: 视频详情响应对象，不存在返回 None
        """
        from app.schemas.video import (
            VideoDetailResponse,
            UploaderBriefResponse,
            CategoryBriefResponse
        )
        
        video = VideoService.get_video_detail(db, video_id)
        if not video:
            return None
        
        # 由于使用了 joinedload，video.uploader 和 video.category 已经预加载
        return VideoDetailResponse(
            id=video.id,
            title=video.title,
            description=video.description,
            cover_url=video.cover_url,
            video_url=video.video_url,
            subtitle_url=video.subtitle_url,
            duration=video.duration,
            status=video.status,
            view_count=VideoService.get_merged_view_count(db, video.id),
            like_count=video.like_count,
            collect_count=video.collect_count,
            uploader=UploaderBriefResponse(
                id=video.uploader.id,
                username=video.uploader.username,
                nickname=video.uploader.nickname,
                avatar=video.uploader.avatar,
            ),
            category=CategoryBriefResponse(
                id=video.category.id,
                name=video.category.name
            ),
            created_at=video.created_at,
        )
    
    @staticmethod
    def get_user_video_list(
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
            status: 视频状态筛选（可选，0=转码中, 1=审核中, 2=已发布, 3=已拒绝, -1=转码失败）
            
        Returns:
            Tuple[List[Video], int]: (视频列表, 总数)
        """
        from sqlalchemy.orm import joinedload
        
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
        
        logger.info(f"查询用户 {user_id} 的视频列表：page={page}, page_size={page_size}, total={total}")
        
        return videos, total
    
    @staticmethod
    def get_user_video_list_response(
        db: Session,
        user_id: int,
        page: int = 1,
        page_size: int = 20,
        status: Optional[int] = None
    ) -> "VideoListResponse":
        """
        获取用户上传的视频列表响应（包含完整的数据组装）
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            page: 页码（从1开始）
            page_size: 每页数量
            status: 视频状态筛选（可选）
            
        Returns:
            VideoListResponse: 视频列表响应对象
        """
        from math import ceil
        from app.schemas.video import (
            VideoListResponse,
            VideoListItemResponse,
            UploaderBriefResponse,
            CategoryBriefResponse
        )
        
        # 获取视频列表和总数
        videos, total = VideoService.get_user_video_list(
            db=db,
            user_id=user_id,
            page=page,
            page_size=page_size,
            status=status,
        )
        
        # 计算总页数
        total_pages = ceil(total / page_size) if total > 0 else 0
        
        # 组装响应数据
        items = []
        for video in videos:
            items.append(
                VideoListItemResponse(
                    id=video.id,
                    title=video.title,
                    description=video.description,
                    cover_url=video.cover_url,
                    duration=video.duration,
                    view_count=VideoService.get_merged_view_count(db, video.id),
                    like_count=video.like_count,
                    collect_count=video.collect_count,
                    uploader=UploaderBriefResponse(
                        id=video.uploader.id,
                        username=video.uploader.username,
                        nickname=video.uploader.nickname,
                        avatar=video.uploader.avatar,
                    ),
                    category=CategoryBriefResponse(
                        id=video.category.id,
                        name=video.category.name
                    ),
                    created_at=video.created_at,
                )
            )
        
        return VideoListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
    
    @staticmethod
    def update_video(
        db: Session,
        video_id: int,
        user_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        category_id: Optional[int] = None
    ) -> Optional[Video]:
        """
        更新视频信息
        
        Args:
            db: 数据库会话
            video_id: 视频ID
            user_id: 用户ID（用于权限验证）
            title: 视频标题（可选）
            description: 视频描述（可选）
            category_id: 分类ID（可选）
            
        Returns:
            Optional[Video]: 更新后的视频对象，不存在或权限不足返回 None
        """
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            logger.warning(f"视频不存在：video_id={video_id}")
            return None
        
        # 权限验证：只有上传者可以编辑
        if video.uploader_id != user_id:
            logger.warning(f"用户 {user_id} 无权编辑视频 {video_id}（上传者：{video.uploader_id}）")
            return None
        
        # 更新字段（只更新非 None 的字段）
        if title is not None:
            video.title = title
        if description is not None:
            video.description = description
        if category_id is not None:
            # 验证分类是否存在
            category = db.query(Category).filter(Category.id == category_id).first()
            if not category:
                logger.warning(f"分类不存在：category_id={category_id}")
                return None
            video.category_id = category_id
        
        db.commit()
        db.refresh(video)
        
        logger.info(f"视频 {video_id} 信息已更新")
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
        video = db.query(Video).filter(Video.id == video_id).first()
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
            db.delete(video)
            logger.info(f"视频 {video_id} 已硬删除")
        else:
            # 软删除：将 status 设置为 4
            video.status = 4
            logger.info(f"视频 {video_id} 已软删除（status=4）")
        
        db.commit()
        return True
