"""
数据统计 API（管理员）
功能：统计概览、趋势分析、分类分布
"""
import json
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
    active_users_today: int  # 今日活跃用户（有观看/点赞/收藏行为）
    total_videos: int
    new_videos_today: int
    total_reports_pending: int
    total_views: int  # 总播放量
    total_likes: int  # 总点赞数
    total_collections: int  # 总收藏数
    videos_pending_review: int  # 待审核视频数


class CategoryStatItem(BaseModel):
    name: str
    count: int


@router.get("/overview", response_model=StatsOverviewResponse, summary="统计概览")
async def stats_overview(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """获取统计概览"""
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # 基础统计
    total_users = db.query(User).count()
    new_users_today = db.query(User).filter(User.created_at >= today).count()
    total_videos = db.query(Video).filter(Video.status == 2).count()
    new_videos_today = db.query(Video).filter(Video.status == 2, Video.created_at >= today).count()
    total_reports_pending = db.query(Report).filter(Report.status == 0).count()
    videos_pending_review = db.query(Video).filter(Video.status == 1).count()
    
    # 今日活跃用户（有观看/点赞/收藏行为）
    from app.models.watch_history import WatchHistory
    from app.models.interaction import UserLike, UserCollection
    
    active_user_ids = set()
    # 今日观看
    watch_users = db.query(WatchHistory.user_id).filter(WatchHistory.watched_at >= today).distinct().all()
    active_user_ids.update([u[0] for u in watch_users])
    # 今日点赞
    like_users = db.query(UserLike.user_id).filter(UserLike.created_at >= today).distinct().all()
    active_user_ids.update([u[0] for u in like_users])
    # 今日收藏
    collect_users = db.query(UserCollection.user_id).filter(UserCollection.created_at >= today).distinct().all()
    active_user_ids.update([u[0] for u in collect_users])
    active_users_today = len(active_user_ids)
    
    # 总播放量、点赞数、收藏数（从数据库聚合）
    total_views = db.query(func.sum(Video.view_count)).scalar() or 0
    total_likes = db.query(func.sum(Video.like_count)).scalar() or 0
    total_collections = db.query(func.sum(Video.collect_count)).scalar() or 0

    return {
        "total_users": total_users,
        "new_users_today": new_users_today,
        "active_users_today": active_users_today,
        "total_videos": total_videos,
        "new_videos_today": new_videos_today,
        "total_reports_pending": total_reports_pending,
        "total_views": int(total_views),
        "total_likes": int(total_likes),
        "total_collections": int(total_collections),
        "videos_pending_review": videos_pending_review
    }


@router.get("/trends", summary="趋势分析")
async def stats_trends(
    days: int = Query(7, le=30),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """获取趋势分析数据（增强版：包含播放量、点赞数等）"""
    end = datetime.utcnow()
    start = end - timedelta(days=days)

    # 初始化日期映射
    date_map = {
        (start + timedelta(days=i)).strftime("%Y-%m-%d"): {
            "user": 0, 
            "video": 0,
            "views": 0,
            "likes": 0,
            "collections": 0
        }
        for i in range(days)
    }

    # 用户注册趋势
    users = db.query(User.created_at).filter(User.created_at >= start).all()
    for u in users:
        d = u.created_at.strftime("%Y-%m-%d")
        if d in date_map:
            date_map[d]["user"] += 1

    # 视频发布趋势（仅已发布）
    videos = db.query(Video.created_at, Video.view_count, Video.like_count, Video.collect_count).filter(
        Video.created_at >= start,
        Video.status == 2
    ).all()
    for v in videos:
        d = v.created_at.strftime("%Y-%m-%d")
        if d in date_map:
            date_map[d]["video"] += 1
            date_map[d]["views"] += v.view_count or 0
            date_map[d]["likes"] += v.like_count or 0
            date_map[d]["collections"] += v.collect_count or 0

    return [
        {
            "date": d,
            "user_count": date_map[d]["user"],
            "video_count": date_map[d]["video"],
            "views": date_map[d]["views"],
            "likes": date_map[d]["likes"],
            "collections": date_map[d]["collections"]
        }
        for d in sorted(date_map.keys())
    ]


@router.get("/categories", response_model=List[CategoryStatItem], summary="分类分布")
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


class ReviewEfficiencyResponse(BaseModel):
    """审核效率统计"""
    pending_count: int  # 待审核数量
    today_approved: int  # 今日通过数
    today_rejected: int  # 今日拒绝数
    avg_review_time_hours: float  # 平均审核时长（小时）


@router.get("/review-efficiency", response_model=ReviewEfficiencyResponse, summary="审核效率统计")
async def review_efficiency(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """获取审核效率统计"""
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # 待审核数量
    pending_count = db.query(Video).filter(Video.status == 1).count()
    
    # 今日审核统计（从 review_report 中解析）
    today_videos = db.query(Video).filter(
        Video.review_status.in_([1, 2]),  # 已通过或已拒绝
        Video.created_at >= today
    ).all()
    
    today_approved = 0
    today_rejected = 0
    review_times = []
    
    for video in today_videos:
        if video.review_report:
            try:
                report = video.review_report if isinstance(video.review_report, dict) else json.loads(video.review_report)
                timestamp_str = report.get("timestamp")
                if timestamp_str:
                    from dateutil import parser
                    review_time = parser.isoparse(timestamp_str)
                    if review_time >= today:
                        if video.review_status == 1:
                            today_approved += 1
                        elif video.review_status == 2:
                            today_rejected += 1
                        # 计算审核时长（从创建到审核）
                        if video.created_at:
                            delta = review_time - video.created_at
                            review_times.append(delta.total_seconds() / 3600)  # 转换为小时
            except Exception:
                pass
    
    avg_review_time_hours = sum(review_times) / len(review_times) if review_times else 0.0
    
    return {
        "pending_count": pending_count,
        "today_approved": today_approved,
        "today_rejected": today_rejected,
        "avg_review_time_hours": round(avg_review_time_hours, 2)
    }

