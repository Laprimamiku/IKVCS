"""
搜索 API

功能：视频搜索、搜索建议
"""
import logging
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.services.search.mysql_search_provider import MySQLSearchProvider
from app.services.search.hotword_service import HotwordService
from app.schemas.video import VideoListResponse, VideoListItemResponse
from app.services.video.video_response_builder import VideoResponseBuilder

logger = logging.getLogger(__name__)

router = APIRouter()


class SearchFilters(BaseModel):
    """搜索筛选条件"""
    category_id: Optional[int] = None
    status: Optional[int] = None  # 默认2（已发布）
    created_from: Optional[str] = None  # ISO 格式日期字符串
    created_to: Optional[str] = None
    duration_min: Optional[int] = None  # 秒
    duration_max: Optional[int] = None
    uploader_id: Optional[int] = None


class SearchSort(BaseModel):
    """排序方式"""
    field: str = "created"  # created/view/like
    order: str = "desc"  # asc/desc


class SearchRequest(BaseModel):
    """搜索请求"""
    q: Optional[str] = None  # 搜索关键词
    filters: Optional[SearchFilters] = None
    sort: Optional[SearchSort] = None
    page: int = 1
    page_size: int = 20


class SearchResponse(BaseModel):
    """搜索响应"""
    items: List[VideoListItemResponse]
    total: int
    page: int
    page_size: int
    suggestions: Optional[List[str]] = None
    highlights: Optional[dict] = None


@router.get("/videos", response_model=SearchResponse, summary="搜索视频")
async def search_videos(
    q: Optional[str] = Query(None, description="搜索关键词"),
    category_id: Optional[int] = Query(None, description="分类ID"),
    status: Optional[int] = Query(2, description="状态（默认2=已发布）"),
    created_from: Optional[str] = Query(None, description="创建时间起始（ISO格式）"),
    created_to: Optional[str] = Query(None, description="创建时间结束（ISO格式）"),
    duration_min: Optional[int] = Query(None, description="时长最小值（秒）"),
    duration_max: Optional[int] = Query(None, description="时长最大值（秒）"),
    uploader_id: Optional[int] = Query(None, description="上传者ID"),
    sort_by: Optional[str] = Query("created", description="排序字段：created/view/like"),
    order: Optional[str] = Query("desc", description="排序方向：asc/desc"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db)
):
    """
    搜索视频（支持高级筛选和排序）
    
    使用 SearchProvider 抽象接口，当前为 MySQL 实现
    """
    # 记录搜索热词
    if q:
        HotwordService.record_search(q)
    
    # 构建筛选条件
    filters = {
        "category_id": category_id,
        "status": status,
        "created_from": created_from,
        "created_to": created_to,
        "duration_min": duration_min,
        "duration_max": duration_max,
        "uploader_id": uploader_id
    }
    # 移除 None 值
    filters = {k: v for k, v in filters.items() if v is not None}
    
    # 构建排序
    sort = {
        "field": sort_by,
        "order": order
    }
    
    # 使用 SearchProvider 搜索
    provider = MySQLSearchProvider(db)
    result = provider.search_videos(
        query=q,
        filters=filters,
        sort=sort,
        page=page,
        page_size=page_size
    )
    
    # 转换为响应格式
    videos = result["items"]
    current_user_id = None  # 公开搜索接口，不包含用户状态
    
    items = VideoResponseBuilder.build_list_items(videos, current_user_id)
    
    return {
        "items": items,
        "total": result["total"],
        "page": result["page"],
        "page_size": result["page_size"],
        "suggestions": result.get("suggestions"),
        "highlights": result.get("highlights")
    }


@router.get("/suggestions", summary="获取搜索建议")
async def get_suggestions(
    q: Optional[str] = Query(None, description="搜索前缀"),
    limit: int = Query(10, ge=1, le=20, description="返回数量"),
    db: Session = Depends(get_db)
):
    """
    获取搜索建议（热词+前缀匹配）
    """
    if not q:
        # 如果没有前缀，返回热词榜
        hotwords = HotwordService.get_hotwords(limit)
        return {
            "suggestions": [h["keyword"] for h in hotwords],
            "hotwords": hotwords
        }
    
    # 获取前缀建议
    suggestions = HotwordService.get_suggestions(q, limit)
    
    return {
        "suggestions": suggestions
    }

