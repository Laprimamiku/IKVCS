"""
管理员服务层
封装管理员相关的业务逻辑
"""
from sqlalchemy.orm import Session
from typing import List, Tuple
from fastapi import HTTPException, status
from datetime import datetime

from app.repositories.report_repository import ReportRepository
from app.repositories.video_repository import VideoRepository
from app.repositories.comment_repository import CommentRepository
from app.repositories.danmaku_repository import DanmakuRepository
from app.core.base_service import BaseService
from app.core.error_codes import ErrorCode
from app.models.report import Report
from app.models.video import Video
from app.models.comment import Comment
from app.models.danmaku import Danmaku


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
        
        if action == "delete_target":
            # 删除目标内容（软删除）
            if report.target_type == "VIDEO":
                video = VideoRepository.get_by_id(db, report.target_id)
                if video:
                    video.status = 4  # 4 表示已删除
            elif report.target_type == "COMMENT":
                comment = CommentRepository.get_by_id_with_relations(db, report.target_id)
                if comment:
                    comment.is_deleted = True
            elif report.target_type == "DANMAKU":
                danmaku = DanmakuRepository.get_by_id(db, report.target_id)
                if danmaku:
                    danmaku.is_deleted = True
            
            report.status = 1  # 已处理
            report.admin_note = admin_note or "管理员删除了违规内容"
        
        elif action == "ignore":
            # 忽略举报
            report.status = 2  # 已忽略
            report.admin_note = admin_note or "管理员判定无违规"
        
        elif action == "disable":
            # 下架/隐藏视频（不删除，仅改变状态）
            if report.target_type == "VIDEO":
                video = VideoRepository.get_by_id(db, report.target_id)
                if video:
                    # 如果视频是已发布状态，改为审核中（临时隐藏）
                    if video.status == 2:
                        video.status = 1  # 改为审核中，用户端不可见
                    # 如果已经是其他状态，保持原状
                report.status = 1  # 已处理
                report.admin_note = admin_note or "管理员下架了视频"
            else:
                # 非视频类型不支持 disable 操作
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="disable 操作仅支持视频类型"
                )
        
        elif action == "request_review":
            # 触发复审（需要冷却/幂等，避免被刷爆）
            # 这里可以添加冷却逻辑，比如检查最近是否已经复审过
            if report.target_type == "VIDEO":
                video = VideoRepository.get_by_id(db, report.target_id)
                if video:
                    # 将视频状态改为审核中，等待人工复审
                    video.status = 1  # 审核中
                    video.review_status = 0  # 重置审核状态为待审核
                report.status = 1  # 已处理
                report.admin_note = admin_note or "管理员请求复审该视频"
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="request_review 操作仅支持视频类型"
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效操作: {action}"
            )
        
        report.handler_id = admin_id
        report.handled_at = datetime.utcnow()
        db.commit()












