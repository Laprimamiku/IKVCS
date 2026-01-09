"""
推荐服务

实现三路召回：热门、同类、个性化
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_

from app.models.video import Video
from app.models.watch_history import WatchHistory
from app.models.interaction import UserLike, UserCollection

logger = logging.getLogger(__name__)


class RecommendationService:
    """推荐服务"""
    
    # 推荐配置
    HOT_LIMIT = 20  # 热门视频数量
    SIMILAR_LIMIT = 10  # 同类视频数量
    PERSONALIZED_LIMIT = 10  # 个性化视频数量
    TOTAL_LIMIT = 20  # 最终返回数量
    
    # 时间衰减配置
    RECENT_DAYS = 30  # 最近 N 天行为有效
    
    @classmethod
    def get_recommendations(
        cls,
        db: Session,
        user_id: Optional[int] = None,
        category_id: Optional[int] = None,
        scene: str = "home",
        limit: int = 20
    ) -> List[Video]:
        """
        获取推荐视频列表
        
        Args:
            db: 数据库会话
            user_id: 用户ID（可选，用于个性化推荐）
            category_id: 分类ID（可选，用于分类推荐）
            scene: 推荐场景（home/detail/category）
            limit: 返回数量
            
        Returns:
            List[Video]: 推荐视频列表
        """
        # 三路召回
        hot_videos = cls._get_hot_videos(db, category_id, cls.HOT_LIMIT)
        similar_videos = cls._get_similar_videos(db, category_id, cls.SIMILAR_LIMIT)
        personalized_videos = []
        
        if user_id:
            personalized_videos = cls._get_personalized_videos(
                db, user_id, cls.PERSONALIZED_LIMIT
            )
        
        # 合并去重
        all_videos = cls._merge_and_deduplicate(
            hot_videos, similar_videos, personalized_videos, user_id
        )
        
        # 限制数量
        return all_videos[:limit]
    
    @classmethod
    def _get_hot_videos(
        cls,
        db: Session,
        category_id: Optional[int] = None,
        limit: int = 20
    ) -> List[Video]:
        """
        获取热门视频（全站/分类）
        
        排序规则：播放量 + 点赞数 + 收藏数（加权）
        """
        from sqlalchemy.orm import joinedload
        
        query = db.query(Video).options(
            joinedload(Video.uploader),
            joinedload(Video.category)
        ).filter(
            Video.status == 2  # 只推荐已发布的视频
        )
        
        if category_id:
            query = query.filter(Video.category_id == category_id)
        
        # 热门排序：综合播放量、点赞数、收藏数
        # 使用简单加权：view_count * 1 + like_count * 3 + collect_count * 5
        videos = query.order_by(
            desc(
                Video.view_count + Video.like_count * 3 + Video.collect_count * 5
            )
        ).limit(limit).all()
        
        return videos
    
    @classmethod
    def _get_similar_videos(
        cls,
        db: Session,
        category_id: Optional[int] = None,
        limit: int = 10
    ) -> List[Video]:
        """
        获取同类视频（同分类/同作者）
        
        如果指定了 category_id，返回同分类视频
        否则返回最新视频
        """
        from sqlalchemy.orm import joinedload
        
        query = db.query(Video).options(
            joinedload(Video.uploader),
            joinedload(Video.category)
        ).filter(
            Video.status == 2
        )
        
        if category_id:
            query = query.filter(Video.category_id == category_id)
        
        # 按创建时间倒序（最新优先）
        videos = query.order_by(desc(Video.created_at)).limit(limit).all()
        
        return videos
    
    @classmethod
    def _get_personalized_videos(
        cls,
        db: Session,
        user_id: int,
        limit: int = 10
    ) -> List[Video]:
        """
        获取个性化推荐视频
        
        基于用户最近 N 天的观看/点赞/收藏行为，计算分类偏好
        """
        from sqlalchemy.orm import joinedload
        from datetime import datetime, timedelta
        
        # 计算时间范围
        cutoff_date = datetime.utcnow() - timedelta(days=cls.RECENT_DAYS)
        
        # 获取用户最近的行为（观看/点赞/收藏）
        # 统计每个分类的行为次数（加权）
        category_weights = {}
        
        # 1. 观看行为（权重 1）
        from sqlalchemy.orm import joinedload
        watch_records = db.query(WatchHistory).options(
            joinedload(WatchHistory.video)
        ).filter(
            WatchHistory.user_id == user_id,
            WatchHistory.watched_at >= cutoff_date
        ).all()
        
        for record in watch_records:
            if record.video and record.video.category_id:
                cat_id = record.video.category_id
                category_weights[cat_id] = category_weights.get(cat_id, 0) + 1
        
        # 2. 点赞行为（权重 3）
        like_records = db.query(UserLike).filter(
            UserLike.user_id == user_id,
            UserLike.target_type == 'video',
            UserLike.created_at >= cutoff_date
        ).all()
        
        # 批量查询视频信息
        like_video_ids = [record.target_id for record in like_records]
        if like_video_ids:
            like_videos = db.query(Video).filter(Video.id.in_(like_video_ids)).all()
            like_video_map = {v.id: v for v in like_videos}
            
            for record in like_records:
                video = like_video_map.get(record.target_id)
                if video and video.category_id:
                    cat_id = video.category_id
                    category_weights[cat_id] = category_weights.get(cat_id, 0) + 3
        
        # 3. 收藏行为（权重 5）
        collect_records = db.query(UserCollection).options(
            joinedload(UserCollection.video)
        ).filter(
            UserCollection.user_id == user_id,
            UserCollection.created_at >= cutoff_date
        ).all()
        
        for record in collect_records:
            if record.video and record.video.category_id:
                cat_id = record.video.category_id
                category_weights[cat_id] = category_weights.get(cat_id, 0) + 5
        
        # 如果没有行为数据，返回空列表（使用热门推荐）
        if not category_weights:
            return []
        
        # 按权重排序，取前 3 个分类
        top_categories = sorted(
            category_weights.items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]
        
        category_ids = [cat_id for cat_id, _ in top_categories]
        
        # 获取这些分类的视频（排除已看过的）
        watched_video_ids_subquery = db.query(WatchHistory.video_id).filter(
            WatchHistory.user_id == user_id
        ).subquery()
        
        query = db.query(Video).options(
            joinedload(Video.uploader),
            joinedload(Video.category)
        ).filter(
            Video.status == 2,
            Video.category_id.in_(category_ids),
            ~Video.id.in_(db.query(watched_video_ids_subquery.c.video_id))
        )
        
        # 按热门度排序
        videos = query.order_by(
            desc(Video.view_count + Video.like_count * 3 + Video.collect_count * 5)
        ).limit(limit).all()
        
        return videos
    
    @classmethod
    def _merge_and_deduplicate(
        cls,
        hot_videos: List[Video],
        similar_videos: List[Video],
        personalized_videos: List[Video],
        user_id: Optional[int] = None
    ) -> List[Video]:
        """
        合并三路召回结果，去重并排序
        
        优先级：个性化 > 同类 > 热门
        """
        seen_ids = set()
        result = []
        
        # 1. 个性化推荐（优先级最高）
        for video in personalized_videos:
            if video.id not in seen_ids:
                result.append(video)
                seen_ids.add(video.id)
        
        # 2. 同类推荐
        for video in similar_videos:
            if video.id not in seen_ids:
                result.append(video)
                seen_ids.add(video.id)
        
        # 3. 热门推荐（填充剩余）
        for video in hot_videos:
            if video.id not in seen_ids:
                result.append(video)
                seen_ids.add(video.id)
        
        return result

