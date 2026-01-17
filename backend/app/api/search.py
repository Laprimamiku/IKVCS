"""
搜索 API

功能：视频搜索、搜索建议
"""
import logging
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from pydantic import BaseModel

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.services.search.mysql_search_provider import MySQLSearchProvider
from app.services.search.hotword_service import HotwordService
from app.schemas.video import VideoListResponse, VideoListItemResponse
from app.schemas.user import UserBriefResponse
from app.models.user import User
from app.models.video import Video
from app.models.video_tag import VideoTag, video_tag_association
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


class UserSearchResponse(BaseModel):
    """用户搜索响应"""
    items: List[UserBriefResponse]
    total: int
    page: int
    page_size: int


@router.get("/videos", response_model=SearchResponse, summary="搜索视频")
async def search_videos(
    q: Optional[str] = Query(None, description="搜索关键词"),
    category_id: Optional[int] = Query(None, description="分类ID"),
    tags: Optional[str] = Query(None, description="标签ID列表（逗号分隔，如：1,2,3）"),
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
    
    # 处理标签搜索
    tag_ids = None
    if tags:
        try:
            tag_ids = [int(tid.strip()) for tid in tags.split(",") if tid.strip()]
            if not tag_ids:
                tag_ids = None
        except ValueError:
            tag_ids = None
    
    # 如果指定了标签，需要先通过标签过滤视频ID
    video_ids_by_tags = None
    if tag_ids:
        # 查询包含指定标签的视频ID
        # 如果多个标签，需要视频同时包含所有标签（AND逻辑）
        video_ids_query = db.query(video_tag_association.c.video_id).filter(
            video_tag_association.c.tag_id.in_(tag_ids)
        )
        
        if len(tag_ids) > 1:
            # 多个标签：需要视频包含所有标签
            # 使用GROUP BY和HAVING COUNT来确保视频包含所有标签
            from sqlalchemy import func
            video_ids_query = video_ids_query.group_by(
                video_tag_association.c.video_id
            ).having(
                func.count(video_tag_association.c.tag_id.distinct()) == len(tag_ids)
            )
        
        video_ids_by_tags = [row[0] for row in video_ids_query.all()]
        if not video_ids_by_tags:
            # 没有符合条件的视频，直接返回空结果
            return {
                "items": [],
                "total": 0,
                "page": page,
                "page_size": page_size,
                "suggestions": None,
                "highlights": None
            }
        
        # 将标签过滤后的视频ID添加到filters中，让MySQLSearchProvider只搜索这些视频
        filters["video_ids"] = video_ids_by_tags
    
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


@router.get("/users", response_model=UserSearchResponse, summary="搜索UP主")
async def search_users(
    q: Optional[str] = Query(None, description="UP主名称（精确匹配）"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    搜索 UP 主（用户名/昵称精确匹配）
    """
    from app.models.user_follow import UserFollow
    
    if not q:
        return {
            "items": [],
            "total": 0,
            "page": page,
            "page_size": page_size,
        }

    base_query = (
        db.query(User)
        .filter(User.status == 1)
        .filter(or_(User.username == q, User.nickname == q))
        .order_by(User.id.desc())
    )

    total = base_query.count()
    offset = (page - 1) * page_size
    users = base_query.offset(offset).limit(page_size).all()

    # 获取当前用户关注的所有用户ID（如果已登录）
    following_user_ids = set()
    if current_user:
        following_relations = db.query(UserFollow.target_user_id).filter(
            UserFollow.user_id == current_user.id
        ).all()
        following_user_ids = {r[0] for r in following_relations}

    # 构建返回项，包含关注状态
    items = []
    for user in users:
        user_dict = UserBriefResponse.model_validate(user).model_dump()
        user_dict["is_following"] = user.id in following_user_ids
        items.append(user_dict)

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }
