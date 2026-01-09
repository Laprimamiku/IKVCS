"""
MySQL 搜索提供者实现

使用 MySQL LIKE 查询实现搜索功能
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, asc

from app.services.search.search_provider import SearchProvider
from app.models.video import Video
from app.models.user import User

logger = logging.getLogger(__name__)


class MySQLSearchProvider(SearchProvider):
    """MySQL 搜索提供者"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def search_videos(
        self,
        query: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        sort: Optional[Dict[str, str]] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """
        MySQL 实现：搜索视频
        """
        from sqlalchemy.orm import joinedload
        
        filters = filters or {}
        sort = sort or {}
        
        # 基础查询：如果 filters 中没有 status，默认只显示已发布的视频（status=2）
        base_query = self.db.query(Video).options(
            joinedload(Video.uploader),
            joinedload(Video.category)
        )
        
        # 如果 filters 中没有指定 status，默认过滤已发布的视频
        if "status" not in filters:
            base_query = base_query.filter(Video.status == 2)
        
        # 应用筛选条件
        query_obj = self._apply_filters(base_query, filters, query)
        
        # 应用排序
        query_obj = self._apply_sort(query_obj, sort)
        
        # 分页
        offset = (page - 1) * page_size
        videos = query_obj.offset(offset).limit(page_size).all()
        
        # 获取总数（轻量查询，不加载关联）
        count_query = self.db.query(func.count(Video.id))
        # 如果 filters 中没有 status，默认过滤已发布的视频
        if "status" not in filters:
            count_query = count_query.filter(Video.status == 2)
        count_query = self._apply_filters(count_query, filters, query, count_only=True)
        total = count_query.scalar() or 0
        
        return {
            "items": videos,
            "total": total,
            "page": page,
            "page_size": page_size,
            "suggestions": None,  # MySQL 实现暂不支持建议
            "highlights": None  # MySQL 实现暂不支持高亮
        }
    
    def _apply_filters(
        self,
        query,
        filters: Dict[str, Any],
        search_query: Optional[str] = None,
        count_only: bool = False
    ):
        """应用筛选条件"""
        from sqlalchemy.orm import joinedload
        
        # 关键词搜索（搜索标题、描述、上传者）
        if search_query:
            keyword_pattern = f"%{search_query}%"
            if count_only:
                # 计数查询需要 join User 表
                query = query.join(User, Video.uploader_id == User.id).filter(
                    or_(
                        Video.title.like(keyword_pattern),
                        Video.description.like(keyword_pattern),
                        User.username.like(keyword_pattern),
                        User.nickname.like(keyword_pattern)
                    )
                )
            else:
                # 列表查询已经 joinedload，直接过滤
                query = query.filter(
                    or_(
                        Video.title.like(keyword_pattern),
                        Video.description.like(keyword_pattern),
                        Video.uploader.has(User.username.like(keyword_pattern)),
                        Video.uploader.has(User.nickname.like(keyword_pattern))
                    )
                )
        
        # 分类筛选
        if filters.get("category_id"):
            query = query.filter(Video.category_id == filters["category_id"])
        
        # 状态筛选（默认已发布，但允许覆盖）
        if "status" in filters:
            query = query.filter(Video.status == filters["status"])
        
        # 时间范围筛选
        if filters.get("created_from"):
            created_from = filters["created_from"]
            if isinstance(created_from, str):
                created_from = datetime.fromisoformat(created_from.replace('Z', '+00:00'))
            query = query.filter(Video.created_at >= created_from)
        
        if filters.get("created_to"):
            created_to = filters["created_to"]
            if isinstance(created_to, str):
                created_to = datetime.fromisoformat(created_to.replace('Z', '+00:00'))
            query = query.filter(Video.created_at <= created_to)
        
        # 时长范围筛选
        if filters.get("duration_min"):
            query = query.filter(Video.duration >= filters["duration_min"])
        
        if filters.get("duration_max"):
            query = query.filter(Video.duration <= filters["duration_max"])
        
        # 上传者筛选
        if filters.get("uploader_id"):
            query = query.filter(Video.uploader_id == filters["uploader_id"])
        
        return query
    
    def _apply_sort(self, query, sort: Dict[str, str]):
        """应用排序"""
        field = sort.get("field", "created")
        order = sort.get("order", "desc")
        
        order_func = desc if order == "desc" else asc
        
        if field == "created":
            query = query.order_by(order_func(Video.created_at))
        elif field == "view":
            query = query.order_by(order_func(Video.view_count))
        elif field == "like":
            query = query.order_by(order_func(Video.like_count))
        else:
            # 默认按创建时间倒序
            query = query.order_by(desc(Video.created_at))
        
        return query

