"""
数据统计 API（管理员）
功能：统计概览、趋势分析、分类分布
"""
import logging
from typing import List
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel

from app.core.database import get_db
from app.core.dependencies import get_current_admin
from app.models.user import User
from app.models.video import Video, Category
from app.models.report import Report

logger = logging.getLogger(__name__)

router = APIRouter()


class StatsOverviewResponse(BaseModel):
    total_users: int
    new_users_today: int
    total_videos: int
    new_videos_today: int
    total_reports_pending: int


class CategoryStatItem(BaseModel):
    name: str
    count: int


@router.get("/statistics/overview", response_model=StatsOverviewResponse, summary="统计概览")
async def stats_overview(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """获取统计概览"""
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    return {
        "total_users": db.query(User).count(),
        "new_users_today": db.query(User).filter(User.created_at >= today).count(),
        "total_videos": db.query(Video).filter(Video.status == 2).count(),
        "new_videos_today": db.query(Video).filter(Video.status == 2, Video.created_at >= today).count(),
        "total_reports_pending": db.query(Report).filter(Report.status == 0).count()
    }


@router.get("/statistics/trends", summary="趋势分析")
async def stats_trends(
    days: int = Query(7, le=30),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """获取趋势分析数据"""
    end = datetime.utcnow()
    start = end - timedelta(days=days)

    users = db.query(User.created_at).filter(User.created_at >= start).all()
    videos = db.query(Video.created_at).filter(Video.created_at >= start).all()

    date_map = {
        (start + timedelta(days=i)).strftime("%Y-%m-%d"): {"user": 0, "video": 0}
        for i in range(days)
    }

    for u in users:
        d = u.created_at.strftime("%Y-%m-%d")
        if d in date_map:
            date_map[d]["user"] += 1

    for v in videos:
        d = v.created_at.strftime("%Y-%m-%d")
        if d in date_map:
            date_map[d]["video"] += 1

    return [
        {
            "date": d,
            "user_count": date_map[d]["user"],
            "video_count": date_map[d]["video"]
        }
        for d in sorted(date_map.keys())
    ]


@router.get("/statistics/categories", response_model=List[CategoryStatItem], summary="分类分布")
async def category_stats(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """获取分类分布统计"""
    results = (
        db.query(Category.name, func.count(Video.id))
        .join(Video, Video.category_id == Category.id)
        .filter(Video.status == 2)
        .group_by(Category.id)
        .all()
    )
    return [{"name": name, "count": count} for name, count in results]

