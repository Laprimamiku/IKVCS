"""
管理员服务层
封装管理员相关的业务逻辑
"""
import math
from sqlalchemy.orm import Session
from typing import List, Tuple, Dict, Any, Optional
from fastapi import HTTPException, status
from datetime import datetime

from app.repositories.report_repository import ReportRepository
from app.repositories.video_repository import VideoRepository
from app.repositories.comment_repository import CommentRepository
from app.repositories.danmaku_repository import DanmakuRepository
from app.core.base_service import BaseService
from app.core.error_codes import ErrorCode
from app.core.video_constants import VideoStatus, ReviewStatus, ReportStatus
from app.models.report import Report
from app.models.video import Video
from app.models.comment import Comment
from app.models.danmaku import Danmaku
from app.schemas.user import UserResponse


class AdminService(BaseService[Report, ReportRepository]):
    """管理员服务"""
    repository = ReportRepository
    
    @staticmethod
    def get_reports(
        db: Session,
        report_status: int = 0,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[Report], int]:
        """
        获取举报列表（包含目标内容预览）
        
        注意：返回所有类型的举报（视频、弹幕、评论），包含 target_snapshot
        
        Args:
            db: 数据库会话
            report_status: 举报状态（0=待处理,1=已处理,2=已忽略）
            page: 页码
            page_size: 每页数量
            
        Returns:
            Tuple[List[Report], int]: (举报列表, 总数)
        """
        from sqlalchemy.orm import joinedload
        from sqlalchemy import desc
        
        # 查询所有类型的举报（包括视频、弹幕、评论）
        query = db.query(Report).filter(
            Report.status == report_status
        )
        total = query.count()
        offset = (page - 1) * page_size
        
        reports = (
            query.options(joinedload(Report.reporter))
            .order_by(desc(Report.created_at))
            .offset(offset)
            .limit(page_size)
            .all()
        )
        
        # 批量查询目标内容，避免 N+1
        # 按类型分组
        video_ids = [r.target_id for r in reports if r.target_type == "VIDEO"]
        comment_ids = [r.target_id for r in reports if r.target_type == "COMMENT"]
        danmaku_ids = [r.target_id for r in reports if r.target_type == "DANMAKU"]
        
        # 批量查询视频
        videos_map = {}
        if video_ids:
            videos = db.query(Video).options(
                joinedload(Video.uploader),
                joinedload(Video.category)
            ).filter(Video.id.in_(video_ids)).all()
            videos_map = {v.id: v for v in videos}
        
        # 批量查询评论
        comments_map = {}
        if comment_ids:
            comments = db.query(Comment).options(
                joinedload(Comment.user),
                joinedload(Comment.video)
            ).filter(Comment.id.in_(comment_ids)).all()
            comments_map = {c.id: c for c in comments}
        
        # 批量查询弹幕
        danmakus_map = {}
        if danmaku_ids:
            danmakus = db.query(Danmaku).options(
                joinedload(Danmaku.user)
            ).filter(Danmaku.id.in_(danmaku_ids)).all()
            danmakus_map = {d.id: d for d in danmakus}
        
        # 为每个举报添加 target_snapshot 属性（动态属性，不修改数据库）
        for report in reports:
            if report.target_type == "VIDEO":
                video = videos_map.get(report.target_id)
                if video:
                    report.target_snapshot = {
                        "id": video.id,
                        "title": video.title,
                        "cover_url": video.cover_url,
                        "video_url": video.video_url,
                        "uploader": {
                            "id": video.uploader.id,
                            "username": video.uploader.username,
                            "nickname": video.uploader.nickname,
                            "avatar": video.uploader.avatar
                        } if video.uploader else None,
                        "status": video.status,
                        "review_status": video.review_status,
                        "created_at": video.created_at.isoformat() if video.created_at else None
                    }
            elif report.target_type == "COMMENT":
                comment = comments_map.get(report.target_id)
                if comment:
                    report.target_snapshot = {
                        "id": comment.id,
                        "content": comment.content,
                        "video_id": comment.video_id,
                        "user": {
                            "id": comment.user.id,
                            "username": comment.user.username,
                            "nickname": comment.user.nickname,
                            "avatar": comment.user.avatar
                        } if comment.user else None,
                        "created_at": comment.created_at.isoformat() if comment.created_at else None
                    }
            elif report.target_type == "DANMAKU":
                danmaku = danmakus_map.get(report.target_id)
                if danmaku:
                    report.target_snapshot = {
                        "id": danmaku.id,
                        "content": danmaku.content,
                        "video_id": danmaku.video_id,
                        "video_time": danmaku.video_time,
                        "user": {
                            "id": danmaku.user.id,
                            "username": danmaku.user.username,
                            "nickname": danmaku.user.nickname,
                            "avatar": danmaku.user.avatar
                        } if danmaku.user else None,
                        "created_at": danmaku.created_at.isoformat() if danmaku.created_at else None
                    }
        
        return reports, total
    
    @staticmethod
    def handle_report(
        db: Session,
        report_id: int,
        action: str,
        admin_id: int,
        admin_note: str = None
    ) -> None:
        """
        处理举报
        
        Args:
            db: 数据库会话
            report_id: 举报ID
            action: 操作类型（delete_target/ignore/disable/request_review）
            admin_id: 管理员ID
            admin_note: 管理员备注
            
        Raises:
            ResourceNotFoundException: 举报不存在
            HTTPException: 无效操作
        """
        report = AdminService.get_by_id_or_raise(
            db, report_id,
            resource_name="举报",
            error_code=ErrorCode.RESOURCE_NOT_FOUND
        )
        
        # 根据操作类型处理举报
        action_handlers = {
            "delete_target": AdminService._handle_delete_target,
            "ignore": AdminService._handle_ignore,
            "disable": AdminService._handle_disable,
            "request_review": AdminService._handle_request_review
        }
        
        handler = action_handlers.get(action)
        if not handler:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效操作: {action}"
            )
        
        handler(db, report, admin_note)
        
        report.handler_id = admin_id
        report.handled_at = datetime.utcnow()
        db.commit()
    
    @staticmethod
    def _handle_delete_target(db: Session, report: Report, admin_note: Optional[str]):
        """处理删除目标内容操作"""
        if report.target_type == "VIDEO":
            video = VideoRepository.get_by_id(db, report.target_id)
            if video:
                video.status = VideoStatus.DELETED  # 已删除
        elif report.target_type == "COMMENT":
            comment = CommentRepository.get_by_id_with_relations(db, report.target_id)
            if comment:
                comment.is_deleted = True
        elif report.target_type == "DANMAKU":
            danmaku = DanmakuRepository.get_by_id(db, report.target_id)
            if danmaku:
                danmaku.is_deleted = True
        
        report.status = ReportStatus.PROCESSED  # 已处理
        report.admin_note = admin_note or "管理员删除了违规内容"
    
    @staticmethod
    def _handle_ignore(db: Session, report: Report, admin_note: Optional[str]):
        """处理忽略举报操作"""
        report.status = ReportStatus.IGNORED  # 已忽略
        report.admin_note = admin_note or "管理员判定无违规"
    
    @staticmethod
    def _handle_disable(db: Session, report: Report, admin_note: Optional[str]):
        """处理下架/隐藏视频操作"""
        if report.target_type != "VIDEO":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="disable 操作仅支持视频类型"
            )
        
        video = VideoRepository.get_by_id(db, report.target_id)
        if video:
            # 如果视频是已发布状态，改为审核中（临时隐藏）
            if video.status == VideoStatus.PUBLISHED:
                video.status = VideoStatus.REVIEWING  # 改为审核中，用户端不可见
            # 如果已经是其他状态，保持原状
        
        report.status = ReportStatus.PROCESSED  # 已处理
        report.admin_note = admin_note or "管理员下架了视频"
    
    @staticmethod
    def _handle_request_review(db: Session, report: Report, admin_note: Optional[str]):
        """处理请求复审操作"""
        if report.target_type != "VIDEO":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="request_review 操作仅支持视频类型"
            )
        
        video = VideoRepository.get_by_id(db, report.target_id)
        if video:
            # 将视频状态改为审核中，等待人工复审
            video.status = VideoStatus.REVIEWING  # 审核中
            video.review_status = ReviewStatus.PENDING  # 重置审核状态为待审核
        
        report.status = ReportStatus.PROCESSED  # 已处理
        report.admin_note = admin_note or "管理员请求复审该视频"
    
    @staticmethod
    def get_reports_response(
        db: Session,
        report_status: int = 0,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """
        获取举报列表响应（包含目标内容预览和跳转链接）
        
        Args:
            db: 数据库会话
            report_status: 举报状态（0=待处理,1=已处理,2=已忽略）
            page: 页码
            page_size: 每页数量
            
        Returns:
            Dict[str, Any]: 举报列表响应（包含 items, total, page, page_size, total_pages）
        """
        reports, total = AdminService.get_reports(db, report_status, page, page_size)
        
        # 构建响应项，添加跳转链接
        items = []
        for report in reports:
            # 构建管理端和公开访问链接
            admin_target_url, public_watch_url = AdminService._build_report_urls(report)
            
            # 构建响应项
            item_dict = {
                "id": report.id,
                "target_type": report.target_type,
                "target_id": report.target_id,
                "reason": report.reason,
                "description": report.description,
                "status": report.status,
                "created_at": report.created_at,
                "reporter": report.reporter,
                "target_snapshot": getattr(report, 'target_snapshot', None),
                "admin_target_url": admin_target_url,
                "public_watch_url": public_watch_url
            }
            items.append(item_dict)
        
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": math.ceil(total / page_size) if total > 0 else 0
        }
    
    @staticmethod
    def _build_report_urls(report: Report) -> Tuple[Optional[str], Optional[str]]:
        """构建举报的管理端和公开访问链接"""
        admin_target_url = None
        public_watch_url = None
        
        if report.target_type == "VIDEO":
            admin_target_url = f"/admin/videos/{report.target_id}"
            public_watch_url = f"/videos/{report.target_id}"
        elif report.target_type == "COMMENT":
            snapshot = getattr(report, 'target_snapshot', None)
            if snapshot and 'video_id' in snapshot:
                admin_target_url = f"/admin/videos/{snapshot['video_id']}"
                public_watch_url = f"/videos/{snapshot['video_id']}"
        elif report.target_type == "DANMAKU":
            snapshot = getattr(report, 'target_snapshot', None)
            if snapshot and 'video_id' in snapshot:
                admin_target_url = f"/admin/videos/{snapshot['video_id']}"
                public_watch_url = f"/videos/{snapshot['video_id']}"
        
        return admin_target_url, public_watch_url












