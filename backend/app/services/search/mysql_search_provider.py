"""
MySQL 搜索提供者实现

使用 MySQL LIKE 查询实现搜索功能
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, asc

from app.services.search.search_provider import SearchProvider
from app.models.video import Video
from app.core.video_constants import VideoStatus

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
        
        实现 SearchProvider 接口，使用 MySQL LIKE 查询实现搜索功能
        
        Args:
            query: 搜索关键词（可选），仅匹配视频标题
            filters: 筛选条件字典
                - category_id: 分类ID
                - status: 视频状态（默认 VideoStatus.PUBLISHED）
                - created_from/to: 创建时间范围
                - duration_min/max: 时长范围
                - uploader_id: 上传者ID
            sort: 排序方式
                - field: 排序字段（created/view/like）
                - order: 排序方向（asc/desc）
            page: 页码（从1开始）
            page_size: 每页数量
            
        Returns:
            Dict[str, Any]: 搜索结果
                - items: 视频列表
                - total: 总数
                - page: 当前页码
                - page_size: 每页数量
                - suggestions: None（MySQL 实现暂不支持）
                - highlights: None（MySQL 实现暂不支持）
        """
        from sqlalchemy.orm import joinedload
        
        filters = filters or {}
        sort = sort or {}
        
        # 基础查询：如果 filters 中没有 status，默认只显示已发布的视频（status=2）
        base_query = self.db.query(Video).options(
            joinedload(Video.uploader),
            joinedload(Video.category)
        )
        
        # 应用默认 status 过滤（如果 filters 中没有指定）
        base_query = self._apply_default_status_filter(base_query, filters)
        
        # 应用筛选条件
        query_obj = self._apply_filters(base_query, filters, query)
        
        # 应用排序
        query_obj = self._apply_sort(query_obj, sort)
        
        # 分页
        offset = (page - 1) * page_size
        videos = query_obj.offset(offset).limit(page_size).all()
        
        # 获取总数（轻量查询，不加载关联）
        count_query = self.db.query(func.count(Video.id))
        count_query = self._apply_default_status_filter(count_query, filters)
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
    
    def _apply_default_status_filter(self, query, filters: Dict[str, Any]):
        """应用默认 status 过滤（如果 filters 中没有指定 status，默认过滤已发布的视频）"""
        if "status" not in filters:
            query = query.filter(Video.status == VideoStatus.PUBLISHED)
        return query
    
    def _apply_filters(
        self,
        query,
        filters: Dict[str, Any],
        search_query: Optional[str] = None,
        count_only: bool = False
    ):
        """应用筛选条件"""
        # 关键词搜索（仅视频标题模糊匹配）
        if search_query:
            keyword_pattern = f"%{search_query}%"
            query = query.filter(Video.title.like(keyword_pattern))
        
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
