"""
推荐 API

功能：视频推荐
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user_optional
from fastapi import Request
from app.models.user import User
from app.services.recommendation.recommendation_service import RecommendationService
from app.services.video.video_response_builder import VideoResponseBuilder
from app.schemas.video import VideoListResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/videos", response_model=VideoListResponse, summary="获取推荐视频")
async def get_recommendations(
    scene: str = Query("home", description="推荐场景：home/detail/category"),
    category_id: Optional[int] = Query(None, description="分类ID（可选）"),
    limit: int = Query(20, ge=1, le=100, description="返回数量"),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    获取推荐视频列表
    
    三路召回：
    1. 热门（全站/分类）
    2. 同类（同分类/同作者）
    3. 个性化（基于用户行为）
    
    去重与冷启动：
    - 新用户：热门+最新
    - 已看过的视频降权/过滤
    """
    # 获取当前用户（可选）
    current_user = get_current_user_optional(request, db)
    user_id = current_user.id if current_user else None
    
    # 获取推荐视频
    videos = RecommendationService.get_recommendations(
        db=db,
        user_id=user_id,
        category_id=category_id,
        scene=scene,
        limit=limit
    )
    
    # 转换为响应格式
    items = VideoResponseBuilder.build_list_items(videos, user_id)
    
    return {
        "items": items,
        "total": len(items),
        "page": 1,
        "page_size": len(items),
        "total_pages": 1
    }

