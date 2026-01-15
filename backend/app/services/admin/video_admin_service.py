"""
视频管理服务（管理员）
职责：处理管理员对视频的审核、封禁、恢复等操作
"""
import json
import math
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, func

from app.repositories.video_repository import VideoRepository
from app.models.video import Video
from app.models.user import User
from app.models.report import Report
from app.core.base_service import BaseService
from app.core.error_codes import ErrorCode
from app.core.video_constants import VideoStatus, ReviewStatus, ReportStatus
from app.services.cache.redis_service import redis_service
from app.utils.timezone_utils import isoformat_in_app_tz, utc_now
from app.utils.json_utils import parse_review_report, safe_json_dumps, dump_json_field
from app.schemas.video import (
    AdminVideoListResponse,
    AdminVideoListItemResponse,
    UploaderBriefResponse,
    CategoryBriefResponse
)

logger = logging.getLogger(__name__)


class VideoAdminService(BaseService[Video, VideoRepository]):
    """视频管理服务（管理员）"""
    repository = VideoRepository
    
    @staticmethod
    def approve_video(
        db: Session,
        video_id: int,
        admin: User
    ) -> dict:
        """
        管理员通过视频审核
        
        Args:
            db: 数据库会话
            video_id: 视频ID
            admin: 管理员用户对象
            
        Returns:
            dict: 包含状态消息的字典
            
        Raises:
            ResourceNotFoundException: 视频不存在
        """
        video = VideoAdminService.get_by_id_or_raise(
            db, video_id,
            resource_name="视频",
            error_code=ErrorCode.VIDEO_NOT_FOUND
        )
        
        # 记录原始状态
        original_status = video.status
        
        # 如果原本是已发布状态，保持已发布；否则设置为已发布
        if original_status == VideoStatus.PUBLISHED:
            # 保持已发布状态，不改变
            video.status = VideoStatus.PUBLISHED
            status_message = "视频已通过审核（保持已发布状态）"
        else:
            # 设置为已发布
            video.status = VideoStatus.PUBLISHED
            status_message = "视频已通过审核"
        
        video.review_status = ReviewStatus.APPROVED  # 审核通过
        
        # 更新审核报告，记录管理员操作
        review_report = {
            "message": "管理员审核通过",
            "timestamp": isoformat_in_app_tz(utc_now()),
            "admin_id": admin.id,
            "admin_username": admin.username,
            "original_status": original_status,
            "final_status": video.status
        }
        
        if video.review_report:
            existing_report = parse_review_report(video.review_report, default={})
            if existing_report:
                review_report.update(existing_report)
                # 清除举报标记（如果存在）
                if "has_report" in review_report:
                    review_report["has_report"] = False
        
        video.review_report = dump_json_field(review_report)
        db.commit()
        
        # 失效相关缓存
        redis_service.invalidate_video_cache(video_id)
        logger.info(
            f"管理员 {admin.username} 通过视频审核: video_id={video_id}, "
            f"original_status={original_status}, final_status={video.status}，已失效相关缓存"
        )
        
        return {"message": status_message}
    
    @staticmethod
    def reject_video(
        db: Session,
        video_id: int,
        admin: User
    ) -> dict:
        """
        管理员拒绝视频审核
        
        Args:
            db: 数据库会话
            video_id: 视频ID
            admin: 管理员用户对象
            
        Returns:
            dict: 包含状态消息的字典
            
        Raises:
            ResourceNotFoundException: 视频不存在
        """
        video = VideoAdminService.get_by_id_or_raise(
            db, video_id,
            resource_name="视频",
            error_code=ErrorCode.VIDEO_NOT_FOUND
        )
        
        video.status = VideoStatus.REJECTED  # 拒绝 / 封禁
        video.review_status = ReviewStatus.REJECTED  # 审核拒绝
        
        # 更新审核报告，记录管理员操作
        review_report = {
            "message": "管理员审核拒绝",
            "timestamp": isoformat_in_app_tz(utc_now()),
            "admin_id": admin.id,
            "admin_username": admin.username
        }
        
        if video.review_report:
            existing_report = parse_review_report(video.review_report, default={})
            if existing_report:
                review_report.update(existing_report)
        
        video.review_report = safe_json_dumps(review_report, ensure_ascii=False)
        db.commit()
        
        # 失效相关缓存
        redis_service.invalidate_video_cache(video_id)
        logger.info(
            f"管理员 {admin.username} 拒绝视频审核: video_id={video_id}，已失效相关缓存"
        )
        
        return {"message": "视频已被拒绝"}
    
    @staticmethod
    def ban_video(
        db: Session,
        video_id: int
    ) -> dict:
        """
        封禁视频
        
        Args:
            db: 数据库会话
            video_id: 视频ID
            
        Returns:
            dict: 包含状态消息的字典
            
        Raises:
            ResourceNotFoundException: 视频不存在
        """
        video = VideoAdminService.get_by_id_or_raise(
            db, video_id,
            resource_name="视频",
            error_code=ErrorCode.VIDEO_NOT_FOUND
        )
        
        video.status = VideoStatus.REJECTED
        db.commit()
        
        # 失效相关缓存
        redis_service.invalidate_video_cache(video_id)
        
        return {"message": "视频已封禁"}
    
    @staticmethod
    def restore_video(
        db: Session,
        video_id: int
    ) -> dict:
        """
        恢复视频发布
        
        Args:
            db: 数据库会话
            video_id: 视频ID
            
        Returns:
            dict: 包含状态消息的字典
            
        Raises:
            ResourceNotFoundException: 视频不存在
        """
        video = VideoAdminService.get_by_id_or_raise(
            db, video_id,
            resource_name="视频",
            error_code=ErrorCode.VIDEO_NOT_FOUND
        )
        
        video.status = VideoStatus.PUBLISHED
        db.commit()
        
        # 失效相关缓存
        redis_service.invalidate_video_cache(video_id)
        
        return {"message": "视频已恢复发布"}
    
    @staticmethod
    def get_manage_videos_response(
        db: Session,
        page: int = 1,
        page_size: int = 20,
        status: Optional[int] = None,
        category_id: Optional[int] = None,
        keyword: Optional[str] = None
    ) -> AdminVideoListResponse:
        """
        获取视频管理列表响应（包含审核信息和举报统计）
        
        Args:
            db: 数据库会话
            page: 页码
            page_size: 每页数量
            status: 状态筛选（可选）
            category_id: 分类筛选（可选）
            keyword: 关键词筛选（可选）
            
        Returns:
            AdminVideoListResponse: 视频管理列表响应
        """
        # 构建查询
        query = db.query(Video)
        
        if status is not None:
            query = query.filter(Video.status == status)
        if category_id is not None:
            query = query.filter(Video.category_id == category_id)
        if keyword:
            query = query.filter(Video.title.like(f"%{keyword}%"))
        
        total = query.count()
        offset = (page - 1) * page_size
        
        # 查询视频列表
        videos = (
            query.options(joinedload(Video.uploader), joinedload(Video.category))
            .order_by(desc(Video.created_at))
            .offset(offset)
            .limit(page_size)
            .all()
        )
        
        if not videos:
            return AdminVideoListResponse(
                items=[],
                total=total,
                page=page,
                page_size=page_size,
                total_pages=math.ceil(total / page_size) if total > 0 else 0
            )
        
        video_ids = [v.id for v in videos]
        
        # 批量读取 Redis 中的播放量，避免列表页逐条访问 Redis（N+1）
        view_count_map = VideoAdminService._get_view_counts_from_redis(video_ids)
        
        # 批量查询举报信息，避免 N+1
        report_stats = VideoAdminService._get_report_stats(db, video_ids)
        
        # 构建响应项
        items = []
        for video in videos:
            # 解析 review_report JSON 字符串
            review_report_dict = VideoAdminService._parse_review_report(video.review_report)
            
            # 获取举报统计信息
            report_info = report_stats.get(video.id, {})
            is_reported = video.id in report_stats
            open_report_count = report_info.get('count', 0)
            last_reported_at = report_info.get('last_reported_at')
            
            items.append(AdminVideoListItemResponse(
                id=video.id,
                title=video.title,
                description=video.description,
                cover_url=video.cover_url,
                video_url=video.video_url or "",
                subtitle_url=video.subtitle_url,
                duration=video.duration,
                status=video.status,
                view_count=view_count_map.get(video.id, video.view_count or 0),
                like_count=video.like_count,
                collect_count=video.collect_count,
                danmaku_count=0,
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
                review_score=video.review_score,
                review_status=video.review_status,
                review_report=review_report_dict,
                is_reported=is_reported,
                open_report_count=open_report_count,
                last_reported_at=last_reported_at,
            ))
        
        return AdminVideoListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=math.ceil(total / page_size)
        )
    
    @staticmethod
    def _get_view_counts_from_redis(video_ids: list[int]) -> Dict[int, int]:
        """批量获取视频播放量（从 Redis）"""
        return redis_service.get_view_counts_batch(video_ids)
    
    @staticmethod
    def _get_report_stats(db: Session, video_ids: list[int]) -> Dict[int, Dict[str, Any]]:
        """批量获取视频举报统计信息"""
        report_stats = {}
        if not video_ids:
            return report_stats
        
        try:
            report_rows = (
                db.query(
                    Report.target_id,
                    func.count(Report.id).label('count'),
                    func.max(Report.created_at).label('last_reported_at')
                )
                .filter(
                    Report.target_type == 'VIDEO',
                    Report.target_id.in_(video_ids),
                    Report.status == ReportStatus.PENDING  # 只统计待处理的举报
                )
                .group_by(Report.target_id)
                .all()
            )
            for row in report_rows:
                report_stats[row.target_id] = {
                    'count': row.count,
                    'last_reported_at': row.last_reported_at
                }
        except Exception:
            pass
        
        return report_stats
    
    @staticmethod
    def _parse_review_report(review_report: Optional[str]) -> Optional[Dict[str, Any]]:
        """解析审核报告 JSON 字符串"""
        return parse_review_report(review_report, default=None)
